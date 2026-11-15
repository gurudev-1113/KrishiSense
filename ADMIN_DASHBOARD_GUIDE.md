# 📊 KrishiSense Admin Dashboard Guide

## Overview

The **Admin Dashboard** provides comprehensive database statistics, user management, telemetry analytics, and system monitoring in a single, intuitive interface.

**Access URL:** `http://localhost:5000/admin/dashboard`

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`

---

## ✨ Dashboard Features

### 1. **Quick Statistics Cards**

The dashboard displays real-time statistics at the top:

```
┌─────────────────┬─────────────────┬─────────────────┐
│  Total Users    │  Sensor Readings│  Active Alerts  │
│  45 users       │  1,245 readings │  3 alerts       │
│  +2 today       │  +89 today      │  12 all-time    │
│  +8 this week   │                 │                 │
└─────────────────┴─────────────────┴─────────────────┘
```

**Metrics shown:**
- **Users**: Total registered, today, this week
- **Telemetry**: Total readings, readings today
- **Alerts**: Active & all-time counts
- **Prices**: Total records, commodities, markets
- **Sensor Averages**: Moisture, temperature, humidity, pH (last 1 hour)

---

### 2. **Tabbed Interface**

Navigate between different data views:

#### **Users Tab**
Shows all registered users with:
- Username
- Email address
- Registration date
- Last login date

```sql
SELECT id, username, email, created_at, last_login 
FROM users 
ORDER BY created_at DESC
```

#### **Telemetry Tab**
Displays latest sensor readings (last 100):
- Timestamp
- Soil moisture (%)
- Temperature (°C)
- Humidity (%)
- pH level

```sql
SELECT * FROM readings 
ORDER BY ts DESC LIMIT 100
```

#### **Alerts Tab**
Shows active and historical alerts:
- Alert type (moisture, temperature, humidity, pH)
- Time raised
- Device ID
- Status (ACTIVE/CLEARED)

```sql
SELECT * FROM alerts 
WHERE ts_raised >= datetime('now', '-30 days')
ORDER BY ts_raised DESC
```

#### **Prices Tab**
Price data statistics:
- Total price records
- Number of commodities tracked
- Number of markets tracked
- Latest price update date

---

## 🔌 API Endpoints

All admin endpoints require admin session authentication.

### **Get All Statistics**
```
GET /api/admin/stats
Response: {
  "users": { "total": 45, "today": 2, "week": 8, "recent": [...] },
  "telemetry": { "total_readings": 1245, "active_alerts": 3, ... },
  "prices": { "total_prices": 5000, "commodities": 35, ... },
  "system": { "total_activities": 500, "today_activities": 12, ... }
}
```

### **Get All Users**
```
GET /api/admin/users
Response: {
  "users": [
    { "id": 1, "username": "farmer1", "email": "farmer@example.com", "created_at": "2024-01-15" },
    ...
  ],
  "total": 45
}
```

### **Get Latest Telemetry**
```
GET /api/admin/telemetry/latest
Response: {
  "readings": [
    { "ts": "2024-11-14T10:30:00", "moisture_pct": 45.3, "air_temp_c": 27.2, ... },
    ...
  ],
  "total": 100
}
```

### **Get Active Alerts**
```
GET /api/admin/alerts/active
Response: {
  "alerts": [
    { "alert_type": "moisture_low", "ts_raised": "2024-11-14T10:15:00", ... },
    ...
  ],
  "total": 3
}
```

### **Get Alert History**
```
GET /api/admin/alerts/history
Response: {
  "alerts": [...],  # Last 30 days
  "total": 42
}
```

### **Get Sensor Statistics**
```
GET /api/admin/sensors/stats
Response: {
  "hourly_stats": [
    { "hour": "2024-11-14 10:00", "reading_count": 6, "avg_moisture": 45.2, ... },
    ...
  ]
}
```

---

## 📋 Database Tables Accessed

The admin dashboard queries these SQLite databases:

### **users.db**
```
users table:
├── id (PRIMARY KEY)
├── username (UNIQUE)
├── email
├── password_hash
├── created_at
└── last_login

activity_log table (optional):
├── id
├── user_id
├── action_type
└── timestamp
```

### **telemetry.db**
```
readings table:
├── id (PRIMARY KEY)
├── device_id
├── ts (timestamp)
├── moisture_pct
├── air_temp_c
├── humidity_pct
├── ph
├── soil_temp_c
└── health_score

alerts table:
├── id (PRIMARY KEY)
├── device_id
├── alert_type (moisture_low, temp_high, etc.)
├── ts_raised
└── ts_cleared
```

### **prices.db**
```
prices table:
├── id
├── Commodity
├── Market
├── Modal_Price
├── Date
└── (other fields)
```

---

## 🔄 Auto-Refresh

The dashboard automatically refreshes statistics every **30 seconds**. This can be adjusted in [templates/admin_dashboard.html](templates/admin_dashboard.html):

```javascript
// Line ~300:
setInterval(loadStats, 30000);  // milliseconds
```

To change to 60 seconds:
```javascript
setInterval(loadStats, 60000);
```

---

## 🎯 Common Admin Tasks

### **Monitor User Growth**
1. Open Admin Dashboard
2. Check "Total Users" card
3. See daily/weekly growth trends

### **Check Sensor Health**
1. Go to **Telemetry Tab**
2. Review latest readings
3. Check for missing data or anomalies

### **Review Active Issues**
1. Go to **Alerts Tab**
2. See active alerts
3. Investigate each one

### **Export User List**
Access via API:
```bash
curl http://localhost:5000/api/admin/users \
  -H "Content-Type: application/json" > users.json
```

### **Export Recent Readings**
Access via API:
```bash
curl http://localhost:5000/api/admin/telemetry/latest \
  -H "Content-Type: application/json" > readings.json
```

---

## 🔐 Security Features

- **Session-based authentication**: Only logged-in admins can access
- **Session check on every endpoint**: All API routes verify `session['is_admin']`
- **Row-level access control**: Admin can see all data (no per-user isolation)
- **No data modification**: Dashboard is read-only (no delete/update operations)

---

## 💾 Database Query Optimizations

Dashboard queries use:
- **Aggregation functions**: COUNT(), AVG(), MAX(), MIN()
- **Date filtering**: Only retrieve recent data (last 7 days for charts, etc.)
- **Limit clauses**: Maximum 100-500 rows per query
- **Indexes on timestamps**: For fast date-range queries

Example optimized query:
```sql
SELECT 
    strftime('%Y-%m-%d %H:00', ts) as hour,
    COUNT(*) as reading_count,
    AVG(moisture_pct) as avg_moisture
FROM readings
WHERE ts >= datetime('now', '-7 days')
GROUP BY hour
ORDER BY hour DESC
LIMIT 24
```

---

## 📊 Sample Dashboard Workflow

### **Morning Check (5 minutes)**
1. Open `/admin/dashboard`
2. Check quick stats cards
3. Review active alerts
4. Note any anomalies
5. Plan interventions if needed

### **Weekly Report (15 minutes)**
1. Export user data via API
2. Export telemetry data via API
3. Create summary report
4. Share with stakeholders

### **Monthly Analysis (30 minutes)**
1. Review all historical data
2. Identify trends
3. Update system configuration
4. Plan maintenance windows

---

## 🐛 Troubleshooting

### **Admin Dashboard Not Loading**

**Problem:** 404 error when accessing `/admin/dashboard`

**Solution:**
1. Ensure you're logged in as admin
2. Check that `admin_dashboard.py` is in the project root
3. Verify the blueprint is registered in `app.py`:
   ```python
   from admin_dashboard import admin_dashboard_bp
   app.register_blueprint(admin_dashboard_bp)
   ```

### **Empty Statistics**

**Problem:** All counters show 0

**Solution:**
1. Check database files exist:
   - `users.db`
   - `telemetry.db`
   - `prices.db`
2. Verify databases have tables (check with SQLite browser)
3. Ensure telemetry is running (`HARDWARE_MODE=simulate` or serial)

### **Slow Dashboard Load**

**Problem:** Dashboard takes > 5 seconds to load

**Solution:**
1. Check database size: Large databases may need indexing
2. Reduce auto-refresh interval from 30s to 60s
3. Archive old data to reduce table sizes
4. Add database indexes on `ts` and `created_at` columns

### **API Returns No Data**

**Problem:** Table shows "no data" even though dashboard loaded

**Solution:**
1. Check browser console for errors (F12 → Console)
2. Verify API endpoint returns data: `curl http://localhost:5000/api/admin/stats`
3. Check Flask app logs for database errors
4. Verify admin session is still active

---

## 🚀 Future Enhancements

Potential improvements to the admin dashboard:

- [ ] **Export to CSV/Excel**: Download data as files
- [ ] **Charts & Graphs**: Visualize trends over time
- [ ] **User Management**: Add/delete users, reset passwords
- [ ] **System Configuration**: Edit alert thresholds
- [ ] **Backup/Restore**: Database management interface
- [ ] **Audit Logs**: Track admin actions
- [ ] **Multi-language**: Translations for dashboard
- [ ] **Dark Mode**: Alternative theme
- [ ] **Real-time Notifications**: WebSocket updates
- [ ] **Advanced Filtering**: Search, sort, date range picker

---

## 📖 Related Documentation

- [COMPLETE_SETUP_SUMMARY.md](COMPLETE_SETUP_SUMMARY.md) — System overview
- [INTEGRATION_STEPS.md](INTEGRATION_STEPS.md) — IoT integration guide
- [IOT_SETUP_GUIDE.md](IOT_SETUP_GUIDE.md) — Detailed IoT setup
- [app.py](app.py) — Main Flask application
- [admin_dashboard.py](admin_dashboard.py) — Backend implementation

---

## 📞 Support

For issues or questions about the admin dashboard:

1. **Check logs**: `python app.py` and look for errors
2. **Read code**: See [admin_dashboard.py](admin_dashboard.py) for implementation details
3. **Review database**: Use SQLite browser to inspect data
4. **Test APIs**: Use curl or Postman to test endpoints

---

**Happy Farming! 🌾📊**

