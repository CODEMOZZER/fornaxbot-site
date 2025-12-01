import psycopg2

conn = psycopg2.connect(
    dbname="defaultdb",
    user="zamozzer",
    password="4bqveY60lK8Vduv1oC6mig",
    host="localhost",
    port=26257,
    sslmode="verify-full",
    sslrootcert="/home/shrmn8/.postgresql/root.crt"
)

cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone())

cur.close()
conn.close()
