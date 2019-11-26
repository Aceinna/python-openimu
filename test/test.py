last_packet_collection = [
    {'packet_type': 'a1', 'data': 'hello1'},
    {'packet_type': 'a2', 'data': 'hello2'},
    {'packet_type': 'a3', 'data': 'hello3'}
]

for x in last_packet_collection:
    if x['packet_type'] == 'a1':
        x['data'] = 'world'
# p[0]['data']='world'

for last_packet in last_packet_collection:
    print(last_packet['packet_type'], last_packet['data'])
