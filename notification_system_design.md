# Campus Notifications Microservice Design Document

## Stage 1 — REST API Design
**Core Actions:**
1. Fetch all notifications for the logged-in student.
2. Mark a specific notification as read.
3. Mark all notifications as read.

### Endpoints
**1. Get User Notifications**
* **URL:** `GET /api/v1/notifications`
* **Headers:** `Authorization: Bearer <token>`
* **Response (200 OK):**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "type": "Placement",
      "message": "CSX Corporation hiring",
      "isRead": false,
      "createdAt": "2026-04-22T17:51:18Z"
    }
  ],
  "pagination": { "page": 1, "totalPages": 5 }
}
```

**2. Mark Notification as Read**
* **URL:** `PATCH /api/v1/notifications/{notificationId}/read`
* **Headers:** `Authorization: Bearer <token>`
* **Response (200 OK):**
```json
{ "status": "success", "message": "Notification marked as read" }
```

**3. Mark All Notifications as Read**
* **URL:** `PATCH /api/v1/notifications/read-all`
* **Headers:** `Authorization: Bearer <token>`
* **Response (200 OK):**
```json
{ "status": "success", "message": "All notifications marked as read" }
```

### Real-Time Notification Method
To push real-time updates (like Placements or Results) to logged-in users, we will use **Server-Sent Events (SSE)** or **WebSockets**.
* **Why WebSockets/SSE?** Polling (the client asking the server for updates every few seconds) creates unnecessary load. WebSockets allow a persistent connection where the server pushes the notification the exact millisecond it is generated, which is efficient and highly responsive.

---

## Stage 2 — Database Design
**Choice:** **PostgreSQL** (Relational Database).
**Why?** Notifications have a strict schema, and we need strong relationships (ACID compliance) between Users and their read states.

**Schema:**
`students` table: `id` (PK), `email`, `name`, `rollNo`
`notifications` table:
* `id` UUID PRIMARY KEY
* `studentID` INT FOREIGN KEY REFERENCES students(id)
* `type` ENUM ('Event', 'Result', 'Placement')
* `message` TEXT
* `isRead` BOOLEAN DEFAULT false
* `createdAt` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

**Scaling Problems & Solutions:**
As data volume increases (millions of notifications), the database will slow down.
* **Solution 1:** **Partitioning**. We can partition the `notifications` table by `createdAt` (e.g., month by month) since older notifications are rarely queried.
* **Solution 2:** **Archiving**. Move notifications older than 6 months to cold storage (like Amazon S3 or a NoSQL archive) to keep the active PostgreSQL tables small and fast.

---

## Stage 3 — Query Optimization
**The Slow Query:**
```sql
SELECT * FROM notifications WHERE studentID = 1042 AND isRead = false ORDER BY createdAt DESC;
```
**Why is it slow?** It has to scan the entire table to find matches for `studentID` and `isRead`, and then sort the results in memory by `createdAt`.

**Indexing Strategy:**
We should create a **Composite B-Tree Index**:
```sql
CREATE INDEX idx_student_unread_recent ON notifications (studentID, isRead, createdAt DESC);
```
**Should we index all columns?** ❌ **No.** Indexing every column severely slows down `INSERT`, `UPDATE`, and `DELETE` operations because the database must update every index whenever a row changes. It also wastes storage space.

**Optimized Query (Find students with placement notifications in last 7 days):**
```sql
SELECT DISTINCT studentID
FROM notifications
WHERE type = 'Placement' 
  AND createdAt >= NOW() - INTERVAL '7 days';
```

---

## Stage 4 — Performance Problem
**Problem:** The DB is overloaded because notifications are fetched on every page load.

**Solutions & Tradeoffs:**
1. **Caching (Redis):** Cache the unread notification count and the top 10 recent notifications for each user in Redis. Read from Redis on page load instead of hitting PostgreSQL.
   * *Tradeoff:* Requires strict cache invalidation logic whenever a new notification is inserted, which adds architectural complexity.
2. **Pagination / Lazy Loading:** Only fetch the first 10 notifications on page load. Fetch more only when the user scrolls down (infinite scroll).
   * *Tradeoff:* Reduces initial DB load but complex to implement cleanly on the frontend.
3. **Push instead of Pull:** Use WebSockets so the frontend doesn't need to fetch on page load; the server just pushes the state when it changes.
   * *Tradeoff:* Maintaining thousands of open WebSocket connections requires dedicated infrastructure (like Socket.io servers or AWS API Gateway).

---

## Stage 5 — System Design Fix
**The Problematic Code:**
```python
# SLOW, NOT RELIABLE, NO RETRY
for student_id in student_ids:
    send_email(student_id, message)
    save_to_db(student_id, message)
    push_to_app(student_id, message)
```
**Why it fails:** If `send_email` takes 1 second, notifying 50,000 students blocks the server for 14 hours! If it crashes at user 200, the remaining 49,800 get nothing, and there's no way to retry the failed ones without sending duplicates to the first 200.

**The Fix:** Use an **Asynchronous Message Queue** (like RabbitMQ or Kafka) and decoupled worker processes.

**Revised Pseudocode:**
```python
# 1. Fast API Endpoint pushes to Queue
function notify_all(student_ids: array, message: string):
    for student_id in student_ids:
        # DB save is critical, do it first
        save_to_db(student_id, message) 
        
        # Push tasks to asynchronous queues (Returns instantly)
        message_queue.push(topic="email_tasks", payload={student_id, message})
        message_queue.push(topic="push_tasks", payload={student_id, message})
    return "Notifications Queued"

# 2. Independent Worker Process (Consumes 'email_tasks' queue)
function email_worker():
    while task = message_queue.pop(topic="email_tasks"):
        try:
            send_email(task.student_id, task.message)
            message_queue.ack(task) # Acknowledge success
        except Exception:
            # Automatic retry logic
            if task.retries < 3:
                message_queue.retry(task)
            else:
                message_queue.move_to_dead_letter_queue(task)
```
**Should DB save and email happen together?** No. Database saves should be synchronous (so the UI updates immediately), while emails should be completely decoupled and asynchronous via queues because emails are slow and prone to network timeouts.

---

## Stage 6 — Priority Inbox
The algorithmic approach to displaying the Top 10 priority notifications involves:
1. **Weighting:** Assigning an integer value to the `Type` (`Placement` = 3, `Result` = 2, `Event` = 1).
2. **Parsing:** Converting the string `Timestamp` into a sortable `datetime` object.
3. **Sorting:** Sorting the array of notifications based on a tuple `(Weight, Timestamp)` in descending order. This guarantees that Placements always appear before Results, and within Placements, the newest ones appear first.
4. **Slicing:** Returning only the first 10 elements of the sorted array.

*(The functioning code for this stage is implemented in the `stage6_code.py` file)*
