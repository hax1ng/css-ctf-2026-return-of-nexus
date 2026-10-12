# Inspection helper: crop each shift gate out of schematic.png into a labelled montage
# with its wired inputs/outputs ringed, used to classify shift A/B sides by eye.
# (needs the full-res schematic.png, which is omitted from the repo for size.)
from parse_svg import paths,labels
from PIL import Image,ImageDraw,ImageFont
ins={0:[65,66],1:[71,72],2:[75,76],3:[85,86],4:[89,90],5:[91,92],6:[105,106],7:[108,109],8:[111,112],9:[120,121],10:[124,125],11:[127,128],12:[129,130]}
outs={0:[69],1:[75,78],2:[77],3:[87],4:[94],5:[93],6:[107],7:[110],8:[113],9:[122],10:[126],11:[130],12:[131]}
im=Image.open('schematic.png').convert('RGB'); scale=3279/1180.8
out=Image.new('RGB',(4*400,4*400),'white'); dr=ImageDraw.Draw(out)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',20)
for j in range(13):
 name=f's{j:02x}'; x,y=labels[name]; cx,cy=round(x*scale),round((y-8)*scale); rad=51
 crop=im.crop((cx-rad,cy-rad,cx+rad,cy+rad)).resize((360,360)); ox=(j%4)*400;oy=(j//4)*400;out.paste(crop,(ox+20,oy+30));d=ImageDraw.Draw(out)
 d.text((ox+8,oy+4),name,font=font,fill='black')
 for ids,sel,col in [(ins[j],'end','blue'),(outs[j],'start','red')]:
  for id in set(ids):
   a,b=paths[id][sel];px=(a*scale-(cx-rad))*360/(2*rad)+ox+20;py=(b*scale-(cy-rad))*360/(2*rad)+oy+30
   d.ellipse((px-5,py-5,px+5,py+5),outline=col,width=2)
   d.text((px+8,py-11),str(id),font=font,fill=col)
out.save('shift_gates_annotated.png')
