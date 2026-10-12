import base64,zlib,gzip,re
from pathlib import Path
expected={0:0xA66FEFC8,1:0x7C3DCD2A,2:0x1812F5CD,3:0xBB1810C0,4:0xD6CCE79E,5:0x6B9F6550,6:0x2A18C562,7:0x3D924BBF}
packets={}; parity={}
for i,line in enumerate(Path('telemetry_raw.txt').read_text().splitlines()):
 fields=dict(kv.split('=',1) for kv in line.split('|')[1:])
 blob=base64.b64decode(fields['DATA'],validate=True)
 assert len(blob)==int(fields['LEN'])
 assert zlib.crc32(blob)==int(fields['WIRECRC'],16)
 if fields['SESSION']!='NX-771':continue
 if fields['TYPE']=='PARITY':parity[fields['GROUP']]=blob;continue
 seq=int(fields['SEQ']);match=zlib.crc32(blob)==expected[seq]
 print('packet',i,'D'+str(seq),'retry',fields['RETRY'],'crc',fields['WIRECRC'],'authoritative',match)
 if match:packets[seq]=blob
# Recover absent packet in each parity group
for missing,group,seqs in [(2,'A',[0,1,3]),(5,'B',[4,6,7])]:
 recovered=bytes(a^b^c^d for a,b,c,d in zip(parity[group],*[packets[s] for s in seqs]))
 packets[missing]=recovered
 print('recovered',missing,hex(zlib.crc32(recovered)).upper(), 'expected',hex(expected[missing]).upper())
 assert zlib.crc32(recovered)==expected[missing]
archive=b''.join(packets[i] for i in range(8))[:5757]
print('original magic:', archive[:10].hex())
archive=b'\x1f\x8b'+archive[2:]
assert archive[:2]==b'\x1f\x8b'
Path('recovered_archive.gz').write_bytes(archive)
print('archive bytes',len(archive),'tail',archive[-20:].hex())
content=gzip.decompress(archive)
Path('recovered_content.bin').write_bytes(content)
print('content bytes',len(content),'prefix',repr(content[:500]))
