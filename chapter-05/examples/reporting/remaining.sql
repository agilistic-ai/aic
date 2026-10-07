SELECT w.id AS workshop_id, w.title AS workshop,
       w.capacity - COALESCE(b.reserved, 0) AS remaining_seats
FROM workshops AS w
LEFT JOIN (
    SELECT workshop_id, SUM(seats) AS reserved
    FROM bookings
    WHERE status = 'confirmed'
    GROUP BY workshop_id
) AS b ON b.workshop_id = w.id
WHERE w.event_date >= ?
ORDER BY w.event_date, w.id
