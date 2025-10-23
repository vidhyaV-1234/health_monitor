#!/usr/bin/env python3
"""
Simple script to check notification status
"""
from stress_notification_system import StressNotificationSystem

print("\n" + "="*70)
print("NOTIFICATION STATUS CHECK")
print("="*70)

print("\n📊 NOTIFICATION THRESHOLDS:")
print("  stress_day > 5:  Level 1 (Moderate) - Wellness reminders")
print("  stress_day > 10: Level 2 (High)     - Stress warning")
print("  stress_day > 50: Level 3 (Critical) - Medical alert")

print("\n🔍 Checking all users...")
s = StressNotificationSystem()
result = s.check_all_users()

print(f"\n📈 SUMMARY:")
print(f"  Total Users: {result['total_users']}")
print(f"  Notifications Sent: {result['notifications_sent']}")

print("\n📋 USER STATUS:")
for r in result.get('results', []):
    user_id = r['user_id']
    status = r['result']['status']
    stress_day = r['result'].get('stress_day', 0)
    
    print(f"\n  User: {user_id}")
    print(f"  Stress Day: {stress_day}")
    print(f"  Status: {status}")
    
    if status == "notification_sent":
        print(f"  ✅ Priority: {r['result']['priority']}")
        print(f"  📨 Message: {r['result']['message']}")
    elif status == "ok":
        print(f"  ✅ Stress level is normal (no notification needed)")
    elif status == "cooldown":
        print(f"  ⏳ Notification cooldown active (wait 2 hours)")

print("\n" + "="*70)

