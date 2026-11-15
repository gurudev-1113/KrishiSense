# 🚀 Admin Dashboard - Quick Reference

## 📍 Access URLs

| Purpose | URL | Login Required |
|---------|-----|---|
| **Admin Dashboard** | http://localhost:5000/admin/dashboard | Yes (admin123/admin123) |
| **User Stats API** | http://localhost:5000/api/admin/users | Yes |
| **Telemetry API** | http://localhost:5000/api/admin/telemetry/latest | Yes |
| **Alerts API** | http://localhost:5000/api/admin/alerts/active | Yes |
| **All Stats API** | http://localhost:5000/api/admin/stats | Yes |

---

## 🎛️ Dashboard Sections

### **Top Navigation (Navigation Bar)**
```
┌─────────────────────────────────────────────────────────────┐
│ 🌾 KrishiSense    Price DSS | Crop | Leaf | Sensor | Insights │ Admin │ [👤 username] [Logout] │
└─────────────────────────────────────────────────────────────┘
```
- **Admin link** appears only for admin users
- Click to access dashboard

---

### **Statistics Cards (Top of Dashboard)**

#### **1. Total Users Card**
```
┌──────────────────────────┐
│ TOTAL USERS              │
│ 45                       │
│ +2 today · +8 this week  │
│ 👥                       │
└──────────────────────────┘
```
**Query**: Counts unique users in `users.db`
**Updates**: Every 30 seconds

#### **2. Sensor Readings Card**
```
┌──────────────────────────┐
│ SENSOR READINGS          │
│ 1,245                    │
│ +89 today                │
│ 📊                       │
└──────────────────────────┘
```
**Query**: Counts all readings in `telemetry.db`
**Updates**: Every 30 seconds

#### **3. Active Alerts Card**
```
┌──────────────────────────┐
│ ACTIVE ALERTS            │
│ 3                        │
│ 12 total all-time        │
│ 🚨                       │
└──────────────────────────┘
```
**Query**: Counts unclosed alerts in `telemetry.db`
**Updates**: Every 30 seconds

#### **4. Price Records Card**
```
┌──────────────────────────┐
│ PRICE RECORDS            │
│ 5,000                    │
│ 35 commodities           │
│ 30 markets               │
│ 💰                       │
└──────────────────────────┘
```
**Query**: Analyzes `prices.db`
**Updates**: Every 30 seconds

#### **5. Average Sensor Values Card**
```
┌──────────────────────────┐
│ AVG VALUES (LAST 1h)     │
│ Moisture: 45.3%          │
│ Temp: 27.2°C             │
│ Humidity: 61%            │
│ pH: 6.54                 │
└──────────────────────────┘
```
**Query**: AVG() on readings WHERE ts >= now - 1 hour
**Updates**: Every 30 seconds

---

### **Tab 1: Users** 👥

```
┌─────────────────────────────────────────────────────────┐
│ [Users] [Telemetry] [Alerts] [Prices] [Refresh]        │
├─────────────────────────────────────────────────────────┤
│ Username     │ Email              │ Registered │ Last   │
├──────────────┼────────────────────┼────────────┼────────┤
│ farmer1      │ farmer1@mail.com   │ 2024-01-15 │ Today  │
│ farmer2      │ farmer2@mail.com   │ 2024-01-14 │ 2h ago │
│ admin        │ admin@mail.com     │ 2024-01-01 │ Now    │
│ ... (all users) ...                                      │
└─────────────────────────────────────────────────────────┘
```
**Data Source**: `users` table
**Columns**: username, email, created_at, last_login
**Sorted By**: Most recent first (created_at DESC)

---

### **Tab 2: Telemetry** 📡

```
┌─────────────────────────────────────────────────────────┐
│ [Users] [Telemetry] [Alerts] [Prices] [Refresh]        │
├─────────────────────────────────────────────────────────┤
│ Time            │ Moisture │ Temperature │ Humidity │ pH │
├─────────────────┼──────────┼─────────────┼──────────┼────┤
│ 14:30:00        │ 45.2%    │ 27.2°C      │ 61.0%    │6.54│
│ 14:20:00        │ 45.3%    │ 27.1°C      │ 60.9%    │6.52│
│ 14:10:00        │ 45.1%    │ 27.3°C      │ 61.2%    │6.56│
│ ... (latest 100) ...                                     │
└─────────────────────────────────────────────────────────┘
```
**Data Source**: `readings` table
**Columns**: ts, moisture_pct, air_temp_c, humidity_pct, ph
**Sorted By**: Most recent first (ts DESC)
**Limit**: Last 100 readings
**Format**: Timestamps in local time

---

### **Tab 3: Alerts** 🚨

```
┌─────────────────────────────────────────────────────────┐
│ [Users] [Telemetry] [Alerts] [Prices] [Refresh]        │
├─────────────────────────────────────────────────────────┤
│ Alert Type           │ Raised       │ Device   │ Status │
├──────────────────────┼──────────────┼──────────┼────────┤
│ 🔴 moisture_low      │ 14:15:00     │ pot-1    │ ACTIVE │
│ 🟡 humidity_high     │ 13:45:00     │ pot-2    │ ACTIVE │
│ 🟠 temp_high         │ 13:30:00     │ pot-1    │ ACTIVE │
│ (older alerts cleared) ...                               │
└─────────────────────────────────────────────────────────┘
```
**Data Source**: `alerts` table
**Columns**: alert_type, ts_raised, device_id, ts_cleared
**Filter**: Only shows recent alerts (last 30 days)
**Status**: ACTIVE (if ts_cleared IS NULL) | CLEARED
**Sorted By**: Most recent first

---

### **Tab 4: Prices** 💰

```
┌─────────────────────────────────────────────────────────┐
│ [Users] [Telemetry] [Alerts] [Prices] [Refresh]        │
├─────────────────────────────────────────────────────────┤
│ Metric                    │ Value                       │
├───────────────────────────┼─────────────────────────────┤
│ Total Price Records       │ 5,000                       │
│ Commodities Tracked       │ 35                          │
│ Markets Tracked           │ 30                          │
│ Latest Update Date        │ 2024-11-14                  │
└─────────────────────────────────────────────────────────┘
```
**Data Source**: `prices` table
**Metrics**:
- COUNT(*) = total records
- COUNT(DISTINCT Commodity) = unique crops
- COUNT(DISTINCT Market) = unique markets
- MAX(Date) = latest update

---

## 🔌 API Usage Examples

### **Get All Stats (Dashboard Cards)**
```bash
curl http://localhost:5000/api/admin/stats \
  -H "Content-Type: application/json"

# Response: All card statistics in one call
{
  "users": {"total": 45, "today": 2, "week": 8},
  "telemetry": {"total_readings": 1245, "active_alerts": 3},
  "prices": {"total_prices": 5000, "commodities": 35},
  "system": {"total_activities": 500}
}
```

### **Export All Users to JSON**
```bash
curl http://localhost:5000/api/admin/users \
  -H "Content-Type: application/json" > users.json

# View file
cat users.json | jq '.users[] | {username, email}'
```

### **Get Recent Sensor Data**
```bash
curl http://localhost:5000/api/admin/telemetry/latest \
  -H "Content-Type: application/json" > readings.json

# Extract last reading
jq '.readings[0]' readings.json
```

### **Monitor Alerts**
```bash
curl http://localhost:5000/api/admin/alerts/active \
  -H "Content-Type: application/json" > alerts.json

# Count active alerts
jq '.total' alerts.json
```

---

## ⏱️ Refresh Behavior

| Component | Auto-Refresh | Manual Refresh |
|-----------|---|---|
| Statistics Cards | Every 30s | Always on page load |
| Users Table | On tab click | Refresh button |
| Telemetry Table | On tab click | Refresh button |
| Alerts Table | On tab click | Refresh button |
| Prices Table | On tab click | Manual query only |

---

## 🔐 Authentication Flow

```
1. User accesses /admin/dashboard
   ↓
2. Flask checks session['is_admin']
   ↓
3. If not admin → redirect to /login
   ↓
4. If admin → render dashboard
   ↓
5. Each API call verifies session['is_admin'] again
   ↓
6. 401 Unauthorized if session invalid
```

---

## 📊 Real-World Usage Scenarios

### **Scenario 1: Daily Morning Check**
```
1. Open admin dashboard (30 seconds)
2. Check total users card → See growth
3. Check active alerts card → Any urgent issues?
4. Click Alerts tab → Review each alert
5. Click Telemetry tab → Verify sensors working
6. Make decisions based on data
```

### **Scenario 2: Weekly Report**
```
1. Open admin dashboard
2. Export users: curl /api/admin/users > users.json
3. Export telemetry: curl /api/admin/telemetry/latest > data.json
4. Export alerts: curl /api/admin/alerts/history > alerts.json
5. Analyze JSON files
6. Create summary report
7. Share with stakeholders
```

### **Scenario 3: New Feature Testing**
```
1. Deploy new feature
2. Monitor dashboard every 5 minutes
3. Watch for new users registering
4. Watch for new sensor data appearing
5. Verify alerts trigger correctly
6. Check API responses with curl
7. Confirm everything working
```

---

## 📱 Mobile Access

**Dashboard is fully responsive:**

```
Desktop (1200px+):
┌──────────────────────────────────────┐
│ Stats Grid (4 columns)               │
│ Tabbed Interface with full tables   │
│ All columns visible                  │
└──────────────────────────────────────┘

Tablet (768px-1199px):
┌────────────────────┐
│ Stats Grid (2 cols)│
│ Tabbed tables      │
│ Horizontal scroll  │
└────────────────────┘

Mobile (< 768px):
┌──────────────┐
│ Stats (1 col)│
│ Tabbed       │
│ Scroll table │
│ (if needed)  │
└──────────────┘
```

---

## 🎯 Key Metrics to Monitor

| Metric | Target | Action if Low | Action if High |
|--------|--------|---|---|
| **New Users/Week** | > 0 | Market campaign | Great! Keep it up |
| **Sensor Readings/Day** | > 100 | Check Arduino | Normal (all devices) |
| **Active Alerts** | < 5 | Investigate | Check thresholds |
| **Avg Moisture** | 40-60% | Water plants | Reduce irrigation |
| **Avg Temperature** | 20-30°C | Check climate | Verify sensors |

---

## 🚨 Alert Thresholds

Current thresholds (see telemetry_module.py):

```
Moisture:
  ├─ Alert if < 20% (too dry)
  └─ Alert if > 80% (too wet)

Temperature:
  ├─ Alert if < 10°C (too cold)
  └─ Alert if > 35°C (too hot)

Humidity:
  ├─ Alert if < 30% (too dry)
  └─ Alert if > 85% (too humid)

pH:
  ├─ Alert if < 6.0 (too acidic)
  └─ Alert if > 8.0 (too alkaline)
```

---

## 💡 Tips & Tricks

1. **Bookmark the dashboard**: Add to bookmarks for quick access
2. **Use curl for automation**: Create monitoring scripts
3. **Export regularly**: Keep backups of data exports
4. **Monitor at same time daily**: Easier to spot patterns
5. **Check last login**: Identify inactive users
6. **Count daily growth**: Calculate user acquisition rate
7. **Track alert trends**: See if issues increasing/decreasing
8. **Verify sensor health**: Look for gaps in telemetry data

---

## ❓ Common Questions

**Q: How often do stats refresh?**
A: Every 30 seconds automatically, or click Refresh button

**Q: Can I download the data?**
A: Yes! Use the API endpoints with curl or Postman

**Q: What if I see 0 for all stats?**
A: Check if databases have data (telemetry.db running?)

**Q: Can regular users access the dashboard?**
A: No, only admin users (after login with admin credentials)

**Q: How do I change alert thresholds?**
A: Edit THRESHOLDS in blueprints/telemetry_module.py

**Q: What's the maximum historical data?**
A: Telemetry: 30 days | Prices: 365 days | Users: unlimited

---

## 📚 Full Documentation

For complete details, see:
- [ADMIN_DASHBOARD_GUIDE.md](ADMIN_DASHBOARD_GUIDE.md) — Complete guide
- [admin_dashboard.py](admin_dashboard.py) — Backend code
- [templates/admin_dashboard.html](templates/admin_dashboard.html) — Frontend code

---

**Ready to use! Access at: http://localhost:5000/admin/dashboard** 🌾📊

