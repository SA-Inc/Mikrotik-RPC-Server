from flask import Flask
from jsonrpc.backend.flask import api
import routeros_api
import sqlite3



# into array to dictionary for result json
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def toDataUnit(num, suffix="B"):
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"



app = Flask(__name__)
app.add_url_rule('/', 'api', api.as_view(), methods=['POST'])

dbConnection = sqlite3.connect('mikrotik_log_db.db', check_same_thread = False)
dbConnection.row_factory = dict_factory
cur = dbConnection.cursor()

routerConnection = routeros_api.RouterOsApiPool(
    host = '10.0.0.1',
    username = 'bot',
    password = '12345678',
    port = 8728,
    plaintext_login = True
)
routerApi = routerConnection.get_api()

# *args - array
# **kwargs - dictionary

# @api.dispatcher.add_method
# def insert(*args, **kwargs):
#     sql = "INSERT INTO t1 (name, number) VALUES (?, ?)"
#     data = (kwargs['name'], kwargs['number'])
#     cur.execute(sql, data)
#     dbConnection.commit()

#     return cur.lastrowid

# @api.dispatcher.add_method
# def update(*args, **kwargs):
#     sql = "UPDATE t1 SET name = ?, number = ? WHERE id = ?"
#     data = (kwargs['name'], kwargs['number'], kwargs['id'])
#     cur.execute(sql, data)
#     dbConnection.commit()

#     return cur.lastrowid

# @api.dispatcher.add_method
# def select(*args, **kwargs):
#     sql = "SELECT id, name, number FROM t1"
#     cur.execute(sql)

#     return cur.fetchall()

# @api.dispatcher.add_method
# def select_id(*args, **kwargs):
#     sql = "SELECT id, name, number FROM t1 WHERE id = ?"
#     data = (kwargs['id'],)
#     cur.execute(sql, data)

#     return cur.fetchall()

# @api.dispatcher.add_method
# def delete(*args, **kwargs):
#     sql = "DELETE FROM t1 WHERE id = ?"
#     data = (kwargs['id'],)
#     cur.execute(sql, data)
#     dbConnection.commit()

#     return cur.lastrowid

@api.dispatcher.add_method
def router_log_total_summary(*args, **kwargs):
    sql = '''
        WITH init AS (
            SELECT 'info' AS 'topic', 0 AS 'topic_count'
            UNION
            SELECT 'error' AS 'topic', 0 AS 'topic_count'
            UNION
            SELECT 'warning' AS 'topic', 0 AS 'topic_count'
            UNION
            SELECT 'critical' AS 'topic', 0 AS 'topic_count'
        )

        SELECT i.topic AS 'topic',
            CASE 
                WHEN a.topic_count IS NOT NULL THEN a.topic_count
                ELSE i.topic_count
            END AS 'topic_count'
        FROM init AS i
        LEFT JOIN (
            SELECT lt.topic, COUNT(topic) AS 'topic_count'
            FROM log AS l
            JOIN log_topic AS lt ON lt.log_id = l.id
            WHERE lt.topic IN ('info', 'error', 'warning', 'critical')
        GROUP BY lt.topic) AS a ON a.topic = i.topic
    '''
    cur.execute(sql)

    result = cur.fetchall()

    return result

@api.dispatcher.add_method
def router_log_today_summary(*args, **kwargs):
    sql = '''
        WITH init AS (
            SELECT 'info' AS 'topic', 0 AS 'topic_count'
            UNION
            SELECT 'error' AS 'topic', 0 AS 'topic_count'
            UNION
            SELECT 'warning' AS 'topic', 0 AS 'topic_count'
            UNION
            SELECT 'critical' AS 'topic', 0 AS 'topic_count'
        )

        SELECT strftime('%d.%m.%Y', date('now')) AS 'date', i.topic AS 'topic',
            CASE 
                WHEN a.topic_count IS NOT NULL THEN a.topic_count
                ELSE i.topic_count
            END AS 'topic_count'
        FROM init AS i
        LEFT JOIN (
            SELECT lt.topic, COUNT(topic) AS 'topic_count'
            FROM log AS l
            JOIN log_topic AS lt ON lt.log_id = l.id
            WHERE strftime('%d.%m.%Y', l.date) = strftime('%d.%m.%Y', date('now')) AND lt.topic IN ('info', 'error', 'warning', 'critical')
        GROUP BY lt.topic) AS a ON a.topic = i.topic
    '''
    cur.execute(sql)

    result = cur.fetchall()

    return result

@api.dispatcher.add_method
def router_log_topics(*args, **kwargs):
    sql = '''
        SELECT DISTINCT topic
        FROM log_topic
    '''

    cur.execute(sql)

    result = cur.fetchall()

    return result

@api.dispatcher.add_method
def router_log_by_topic(*args, **kwargs):
    sql = '''
        SELECT l.id, strftime('%d.%m.%Y %H:%M:%S', l.date) AS 'date', l.message
        FROM log AS l
        JOIN log_topic AS lt ON lt.log_id = l.id
        WHERE lt.topic = ? AND l.date BETWEEN strftime('%d.%m.%Y', date('now', '-7 days')) AND strftime('%d.%m.%Y', date('now'))
        ORDER BY l.id DESC
    '''

    cur.execute(sql, (kwargs['topic'],))

    result = cur.fetchall()

    return result

@api.dispatcher.add_method
def router_info(*args, **kwargs):
    firewallFilter = routerApi.get_resource('/ip/firewall/filter')
    firewallFilterData = firewallFilter.get()

    identity = routerApi.get_resource('/system/identity')
    identityData = identity.get()

    resource = routerApi.get_resource('/system/resource')
    resourceData = resource.get()

    # result data
    routerInfo = {}

    for entry in firewallFilterData:
        if (entry['id'] == '*1'): # Upload
            routerInfo['total_upload_size'] = toDataUnit(int(entry['bytes']))
            routerInfo['total_upload_packets'] = entry['packets']
        if (entry['id'] == '*2'): # Download
            routerInfo['total_download_size'] = toDataUnit(int(entry['bytes']))
            routerInfo['total_download_packets'] = entry['packets']

    routerInfo['identity'] = identityData[0]['name']
    routerInfo['uptime'] = resourceData[0]['uptime']
    routerInfo['cpu-load'] = resourceData[0]['cpu-load']
    routerInfo['free-memory'] = toDataUnit(int(resourceData[0]['free-memory']))
    routerInfo['load-memory'] = toDataUnit(int(resourceData[0]['total-memory']) - int(resourceData[0]['free-memory']))
    routerInfo['total-memory'] = toDataUnit(int(resourceData[0]['total-memory']))
    routerInfo['free-hdd-space'] = toDataUnit(int(resourceData[0]['free-hdd-space']))
    routerInfo['load-hdd-space'] = toDataUnit(int(resourceData[0]['total-hdd-space']) - int(resourceData[0]['free-hdd-space']))
    routerInfo['total-hdd-space'] = toDataUnit(int(resourceData[0]['total-hdd-space']))
    routerInfo['board-name'] = resourceData[0]['board-name']
    routerInfo['platform'] = resourceData[0]['platform']
    routerInfo['version'] = resourceData[0]['version']

    return routerInfo

@api.dispatcher.add_method
def router_dhcp_server(*args, **kwargs):
    dhcp = routerApi.get_resource('/ip/dhcp-server/lease')
    dhcpData = dhcp.get()

    print(dhcpData)

    result = []

    for entry in dhcpData:
        result.append({
            'address': entry['address'],
            'status': entry['status'],
            'host_name': entry['host-name'] if 'host-name' in entry else '',
            'expires_after': entry['expires-after'] if 'expires-after' in entry else '',
            'last_seen': entry['last-seen'] if 'last-seen' in entry else '',
        })

    return result

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 3500, debug = True)