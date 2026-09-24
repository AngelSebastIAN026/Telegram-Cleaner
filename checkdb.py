import sqlite3


connection = sqlite3.connect("channels.db")

print("\nTables in database:")
print("--------------------------------")

tables = connection.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

for table in tables:
    print(table[0])


print("\nPending invites:")
print("--------------------------------")

pending_invites = connection.execute(
    "SELECT * FROM pending_invites"
).fetchall()

for invite in pending_invites:
    print(invite)


connection.close()