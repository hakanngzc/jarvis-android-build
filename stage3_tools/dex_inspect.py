import struct, sys
from pathlib import Path

OP_WIDTH = [1]*256
for op in [0x02,0x05,0x08]: OP_WIDTH[op]=2
for op in [0x03,0x06,0x09]: OP_WIDTH[op]=3
for op in range(0x13,0x17): OP_WIDTH[op]=2
OP_WIDTH[0x17]=3; OP_WIDTH[0x18]=5; OP_WIDTH[0x19]=2
OP_WIDTH[0x1a]=2; OP_WIDTH[0x1b]=3; OP_WIDTH[0x1c]=2
OP_WIDTH[0x1f]=2; OP_WIDTH[0x20]=2; OP_WIDTH[0x22]=2; OP_WIDTH[0x23]=2; OP_WIDTH[0x24]=3; OP_WIDTH[0x25]=3; OP_WIDTH[0x26]=3
OP_WIDTH[0x29]=2; OP_WIDTH[0x2a]=3; OP_WIDTH[0x2b]=3; OP_WIDTH[0x2c]=3
for op in range(0x2d,0x3e): OP_WIDTH[op]=2
for op in range(0x44,0x6e): OP_WIDTH[op]=2
for op in range(0x6e,0x73): OP_WIDTH[op]=3
for op in range(0x74,0x79): OP_WIDTH[op]=3
for op in range(0x90,0xb0): OP_WIDTH[op]=2
for op in range(0xd0,0xe3): OP_WIDTH[op]=2
for op in [0xfa,0xfb,0xfc,0xfd]: OP_WIDTH[op]=3
OP_WIDTH[0xfe]=2; OP_WIDTH[0xff]=2

OP_NAMES = {
0x00:'nop',0x01:'move',0x02:'move/from16',0x03:'move/16',0x04:'move-wide',0x05:'move-wide/from16',0x06:'move-wide/16',0x07:'move-object',0x08:'move-object/from16',0x09:'move-object/16',
0x0a:'move-result',0x0b:'move-result-wide',0x0c:'move-result-object',0x0d:'move-exception',0x0e:'return-void',0x0f:'return',0x10:'return-wide',0x11:'return-object',
0x12:'const/4',0x13:'const/16',0x14:'const',0x15:'const/high16',0x16:'const-wide/16',0x17:'const-wide/32',0x18:'const-wide',0x19:'const-wide/high16',
0x1a:'const-string',0x1b:'const-string/jumbo',0x1c:'const-class',0x1d:'monitor-enter',0x1e:'monitor-exit',0x1f:'check-cast',0x20:'instance-of',0x21:'array-length',0x22:'new-instance',0x23:'new-array',0x24:'filled-new-array',0x25:'filled-new-array/range',0x26:'fill-array-data',0x27:'throw',0x28:'goto',0x29:'goto/16',0x2a:'goto/32',0x2b:'packed-switch',0x2c:'sparse-switch',
0x2d:'cmpl-float',0x2e:'cmpg-float',0x2f:'cmpl-double',0x30:'cmpg-double',0x31:'cmp-long',
0x32:'if-eq',0x33:'if-ne',0x34:'if-lt',0x35:'if-ge',0x36:'if-gt',0x37:'if-le',0x38:'if-eqz',0x39:'if-nez',0x3a:'if-ltz',0x3b:'if-gez',0x3c:'if-gtz',0x3d:'if-lez',
0x44:'aget',0x45:'aget-wide',0x46:'aget-object',0x47:'aget-boolean',0x48:'aget-byte',0x49:'aget-char',0x4a:'aget-short',0x4b:'aput',0x4c:'aput-wide',0x4d:'aput-object',0x4e:'aput-boolean',0x4f:'aput-byte',0x50:'aput-char',0x51:'aput-short',
0x52:'iget',0x53:'iget-wide',0x54:'iget-object',0x55:'iget-boolean',0x56:'iget-byte',0x57:'iget-char',0x58:'iget-short',0x59:'iput',0x5a:'iput-wide',0x5b:'iput-object',0x5c:'iput-boolean',0x5d:'iput-byte',0x5e:'iput-char',0x5f:'iput-short',
0x60:'sget',0x61:'sget-wide',0x62:'sget-object',0x63:'sget-boolean',0x64:'sget-byte',0x65:'sget-char',0x66:'sget-short',0x67:'sput',0x68:'sput-wide',0x69:'sput-object',0x6a:'sput-boolean',0x6b:'sput-byte',0x6c:'sput-char',0x6d:'sput-short',
0x6e:'invoke-virtual',0x6f:'invoke-super',0x70:'invoke-direct',0x71:'invoke-static',0x72:'invoke-interface',0x74:'invoke-virtual/range',0x75:'invoke-super/range',0x76:'invoke-direct/range',0x77:'invoke-static/range',0x78:'invoke-interface/range',
}
for i,n in enumerate(['neg-int','not-int','neg-long','not-long','neg-float','neg-double','int-to-long','int-to-float','int-to-double','long-to-int','long-to-float','long-to-double','float-to-int','float-to-long','float-to-double','double-to-int','double-to-long','double-to-float','int-to-byte','int-to-char','int-to-short'],0x7b): OP_NAMES[i]=n
binops=['add-int','sub-int','mul-int','div-int','rem-int','and-int','or-int','xor-int','shl-int','shr-int','ushr-int','add-long','sub-long','mul-long','div-long','rem-long','and-long','or-long','xor-long','shl-long','shr-long','ushr-long','add-float','sub-float','mul-float','div-float','rem-float','add-double','sub-double','mul-double','div-double','rem-double']
for i,n in enumerate(binops,0x90): OP_NAMES[i]=n
for i,n in enumerate(['add-int/lit16','rsub-int','mul-int/lit16','div-int/lit16','rem-int/lit16','and-int/lit16','or-int/lit16','xor-int/lit16'],0xd0): OP_NAMES[i]=n
for i,n in enumerate(['add-int/lit8','rsub-int/lit8','mul-int/lit8','div-int/lit8','rem-int/lit8','and-int/lit8','or-int/lit8','xor-int/lit8','shl-int/lit8','shr-int/lit8','ushr-int/lit8'],0xd8): OP_NAMES[i]=n

class Dex:
 def __init__(self,path):
  self.b=Path(path).read_bytes(); b=self.b
  if not b.startswith(b'dex\n'): raise ValueError('not dex')
  vals=struct.unpack_from('<20I',b,0x38)
  (self.string_n,self.string_off,self.type_n,self.type_off,self.proto_n,self.proto_off,self.field_n,self.field_off,self.method_n,self.method_off,self.class_n,self.class_off,*_)=vals
  self.strings=[self._string(struct.unpack_from('<I',b,self.string_off+4*i)[0]) for i in range(self.string_n)]
  self.types=[self.strings[struct.unpack_from('<I',b,self.type_off+4*i)[0]] for i in range(self.type_n)]
  self.methods=[]
  for i in range(self.method_n):
   ci,pi,ni=struct.unpack_from('<HHI',b,self.method_off+8*i); self.methods.append((self.types[ci],self.strings[ni],pi))
  self.fields=[]
  for i in range(self.field_n):
   ci,ti,ni=struct.unpack_from('<HHI',b,self.field_off+8*i); self.fields.append((self.types[ci],self.strings[ni],self.types[ti]))
 def uleb(self,o):
  r=0;s=0
  while True:
   x=self.b[o];o+=1;r|=(x&0x7f)<<s
   if x<128:return r,o
   s+=7
 def _string(self,o):
  _,o=self.uleb(o); e=self.b.index(0,o); return self.b[o:e].decode('utf-8','replace')
 def class_methods(self,desc):
  b=self.b
  for j in range(self.class_n):
   vals=struct.unpack_from('<8I',b,self.class_off+32*j); class_idx=vals[0]; data_off=vals[6]
   if self.types[class_idx]!=desc or not data_off: continue
   o=data_off; sf,o=self.uleb(o); inf,o=self.uleb(o); dm,o=self.uleb(o); vm,o=self.uleb(o)
   for _ in range(sf+inf): _,o=self.uleb(o);_,o=self.uleb(o)
   out=[]
   for kind,count in [('direct',dm),('virtual',vm)]:
    mid=0
    for _ in range(count):
     diff,o=self.uleb(o); mid+=diff; access,o=self.uleb(o); code,o=self.uleb(o); out.append((kind,mid,self.methods[mid],access,code))
   return out
  return []
 def disasm(self,code_off,limit=10000):
  if not code_off:return []
  b=self.b; regs,ins,outs,tries=struct.unpack_from('<4H',b,code_off); debug,sz=struct.unpack_from('<2I',b,code_off+8); p=code_off+16
  units=list(struct.unpack_from('<%dH'%sz,b,p)); out=[]; i=0
  while i<len(units) and len(out)<limit:
   u=units[i]; op=u&0xff; name=OP_NAMES.get(op,f'op_{op:02x}'); w=OP_WIDTH[op]
   if op==0 and (u>>8) in (1,2,3):
    ident=u>>8
    if ident==1: size=units[i+1]; w=4+size*2; name='packed-switch-payload'
    elif ident==2: size=units[i+1]; w=2+size*4; name='sparse-switch-payload'
    else: elem_width=units[i+1]; size=units[i+2]|(units[i+3]<<16); w=4+(elem_width*size+1)//2; name='array-data-payload'
   args=''
   try:
    if op==0x1a: args=repr(self.strings[units[i+1]])
    elif op==0x1b: args=repr(self.strings[units[i+1]|(units[i+2]<<16)])
    elif op in range(0x6e,0x73) or op in range(0x74,0x79):
     idx=units[i+1]; cls,mn,_=self.methods[idx]; args=f'{cls}->{mn} [method@{idx}]'
    elif op in range(0x52,0x6e):
     idx=units[i+1]; cls,fn,ft=self.fields[idx]; args=f'{cls}->{fn}:{ft} [field@{idx}]'
    elif op in (0x22,0x1c,0x1f,0x20,0x23): args=self.types[units[i+1]]
   except Exception as e: args=f'<decode err {e}>'
   raw=' '.join(f'{x:04x}' for x in units[i:i+w]); out.append((i,name,args,raw)); i+=max(w,1)
  return (regs,ins,outs,tries,sz,out)

if __name__=='__main__':
 d=Dex(sys.argv[1]); cls=sys.argv[2]
 print('class',cls)
 for kind,mid,m,acc,code in d.class_methods(cls):
  if len(sys.argv)>3 and sys.argv[3].lower() not in m[1].lower(): continue
  print('\nMETHOD',kind,mid,m,'access',hex(acc),'code',hex(code))
  if code:
   regs,ins,outs,tries,sz,items=d.disasm(code); print('regs/ins/outs/tries/units',regs,ins,outs,tries,sz)
   for off,n,args,raw in items: print(f'{off:05x}: {raw:<28} {n:<25} {args}')
