"""A separately composed, linked 27-page architectural sales publication."""
from pathlib import Path
from html import escape
import io,json
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from project_data import *

A=PUBLIC/'assets';OUT=PUBLIC/'brozura.pdf'
PUBLIC.mkdir(parents=True,exist_ok=True)
for name,file in [('Sans','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf'),('Serif','DejaVuSerif.ttf')]:
 pdfmetrics.registerFont(TTFont(name,str(ROOT/'fonts'/file)))
W,H=595.28,841.89;M=42;CW=W-2*M
INK='#20382f';PAPER='#f5f2e9';BRASS='#8a6e42';MUTED='#616c61';LINE='#d5d6c9';LIGHT='#c4cdbe'
c=canvas.Canvas(str(OUT),pagesize=(W,H),pageCompression=1)
c.setTitle('Viladům v zahradách | Louny | říjen 2026');c.setAuthor('Viladům v zahradách');c.setSubject(MAIN_LINE)
c.setViewerPreference('DisplayDocTitle','true')
page_number=0;cache={};metrics=[]

def plain(value):return value.replace('–','-').replace('—','-')
def text(x,y,value,size=11,font='Sans',color=INK,right=False):
 value=plain(str(value));c.setFillColor(color);c.setFont(font,size)
 if right:c.drawRightString(x,y,value)
 else:c.drawString(x,y,value)

def para(value,x,top,width=CW,size=11,color=INK,font='Sans',leading=None):
 p=Paragraph(plain(value),ParagraphStyle('p',fontName=font,fontSize=size,leading=leading or size*1.52,textColor=color,spaceAfter=0))
 _,height=p.wrap(width,900);p.drawOn(c,x,top-height)
 metrics.append({'page':page_number,'text':value[:50],'bottom':round(top-height,1),'height':round(height,1)})
 return top-height

def line(y,x1=M,x2=W-M,color=LINE):
 c.setStrokeColor(color);c.setLineWidth(.55);c.line(x1,y,x2,y)

def rect(x,y,w,h,color):
 c.setFillColor(color);c.rect(x,y,w,h,fill=1,stroke=0)

def page(kicker,title,bookmark=None,dark=False):
 global page_number
 page_number+=1;rect(0,0,W,H,INK if dark else PAPER)
 color=PAPER if dark else INK
 text(M,H-48,kicker.upper(),8.5,'Sans','#c7ad76' if dark else BRASS)
 para(title.replace('\n','<br/>'),M,H-83,CW,32,color,'Serif',39)
 line(42,color='#637466' if dark else LINE)
 text(M,25,'VILADŮM V ZAHRADÁCH / LOUNY',7.5,'Sans',LIGHT if dark else MUTED)
 text(W-M,25,f'{page_number:02}',9,'Sans',LIGHT if dark else MUTED,right=True)
 if bookmark:
  c.bookmarkPage(bookmark);c.addOutlineEntry(plain(title or 'Viladům v zahradách'),bookmark,0,False)

def finish():c.showPage()

def image(name,x,y,w,h):
 key=name
 if key not in cache:
  if name=='house':im=Image.open(ROOT/'images/house-original.jpg').crop((0,238,1419,1476)).convert('RGB')
  else:im=Image.open(A/name).convert('RGB')
  dimensions=im.size
  if name=='house' or (name.endswith('.webp') and not name.startswith('archviz-')):
   im.thumbnail((1660,1660));buf=io.BytesIO();im.save(buf,format='JPEG',quality=85,optimize=True,subsampling=0);buf.seek(0);reader=ImageReader(buf)
  elif name.startswith('archviz-') or name=='garden.png':
   # Material presentation stays sharp at source resolution; technical originals remain lossless.
   buf=io.BytesIO();im.save(buf,format='JPEG',quality=96,optimize=True,subsampling=0);buf.seek(0);reader=ImageReader(buf)
  else:
   if name.startswith(('plan-','section-','scale-','site')):im=im.convert('L')
   reader=ImageReader(im)
  cache[key]=(reader,dimensions)
 reader,(iw,ih)=cache[key];s=min(w/iw,h/ih)
 c.drawImage(reader,x+(w-iw*s)/2,y+(h-ih*s)/2,width=iw*s,height=ih*s)

def link(label,x,y,url,size=9,color=BRASS):
 text(x,y,label,size,'Sans',color)
 width=pdfmetrics.stringWidth(plain(label),'Sans',size)
 c.linkURL(url,(x,y-4,x+width,y+size+3),relative=0,thickness=0)

def button(label,x,y,w,url,dark=True):
 rect(x,y,w,40,INK if dark else PAPER);text(x+15,y+15,label,10,'Sans',PAPER if dark else INK)
 c.linkURL(url,(x,y,x+w,y+40),relative=0,thickness=0)

def unit_visual(u):
 a,floor,layout,total,photos,rooms,sections=u;title,desc,facts=CHARACTERS[a]
 page(floor+' / Byt '+a,'Byt '+a+' / '+layout.replace(' + ','+'),'byt-'+a.lower())
 text(M,700,total+' m²',24,'Serif');text(230,702,'celkem dle projektu',9,'Sans',MUTED)
 if a in 'AD':
  rect(M,348,CW,314,'#ffffff');image('archviz-'+a.lower()+'.webp',M+14,362,CW-28,286)
  text(M,332,'Materiálový půdorys / návrh vybavení',8.5,'Sans',MUTED)
  title_bottom=para(title,M,305,280,25,INK,'Serif',31)
  para(desc,M,title_bottom-15,277,10.5)
  image(photos[0][0]+'.webp',350,136,203,154)
  text(350,118,'Koupelna / vizualizace',8,'Sans',MUTED)
 else:
  rect(M,325,CW,338,'#e9e8dc');image(photos[0][0]+'.webp',M,325,CW,338)
  text(M,305,photos[0][1]+' / vizualizace, návrh vybavení',8.5,'Sans',MUTED)
  bottom=para(title,M,278,CW,26,INK,'Serif',32)
  para(desc,M,bottom-17,CW,11)
 for i,(value,label) in enumerate(facts):
  x=M+i*174;text(x,88,value,23,'Serif');para(label,x,72,155,8.5,MUTED)
 finish()

def unit_plan(u):
 a,floor,layout,total,photos,rooms,sections=u;k=a.lower()
 page('Byt '+a+' / Půdorys a výměry',total+' m² pro váš život')
 rect(M,404,CW,280,'#ffffff')
 name=('plan-'+k+'.png') if a in 'AD' else ('archviz-'+k+'.webp')
 image(name,M+12,416,CW-24,256)
 text(M,389,'Původní projektový půdorys' if a in 'AD' else 'Materiálový půdorys / návrh vybavení',8.5,'Sans',MUTED)
 link('Otevřít původní technický výkres',M,370,SITE_URL+'/assets/plan-'+k+'.png',8.5)
 text(M,341,'Výměry místností',19,'Serif')
 text(M,317,'ČÍSLO',8,'Sans',MUTED);text(100,317,'MÍSTNOST',8,'Sans',MUTED);text(374,317,'m²',8,'Sans',MUTED,right=True)
 y=293
 for number,room,area in rooms:
  text(M,y,number,9.5,'Sans',MUTED);text(100,y,room,10.5);text(374,y,area,10.5,right=True);line(y-9,M,374);y-=23
 text(M,y-1,'Celkem dle projektu',10,'Bold');text(374,y-1,total,11,'Bold',right=True)
 text(410,317,'PROJEKTOVÉ ŘEZY',8,'Sans',MUTED)
 if len(sections)==1:image(sections[0]+'.png',402,155,151,135)
 else:
  image(sections[0]+'.png',402,203,151,87);image(sections[1]+'.png',402,104,151,87)
 image('scale-'+k+'.png',402,94 if len(sections)==1 else 73,151,38)
 if a in 'DE':para(LOFT_NOTE,M,100,335,8.5,MUTED,leading=11)
 else:link('Získat aktuální nabídku bytu '+a,M,74,'mailto:'+EMAIL+'?subject=Byt%20'+a,9)
 finish()

# 01 - A cover built from the supplied, actual photograph.
page('Osvoboditelů 497 / Louny','',bookmark='uvod',dark=True)
text(M,744,'Viladům',53,'Serif',PAPER);text(M,677,'v zahradách',48,'Serif',PAPER)
image('house',M,185,CW,445)
text(M,144,'Historie v architektuře.',24,'Serif',PAPER);text(M,108,'Prostor pro váš život.',24,'Serif',PAPER)
text(M,67,'6 bytů / 82,25-116,45 m² celkem dle projektu',10,'Sans',LIGHT)
finish()

# 02 - Narrative with the original architecture kept separate from the proposal.
page('01 / Dům','Dům s minulostí.\nŽivot před vámi.','dum')
para(STORY,M,678,CW,12)
text(M,608,PROJECT_ADDRESS,10,'Sans',BRASS)
image('01-living.webp',M,286,CW,306)
text(M,268,'Obytný prostor / vizualizace, návrh vybavení',8.5,'Sans',MUTED)
para(SECOND,M,231,CW,11)
line(130);text(M,101,'6',32,'Serif');text(104,103,'osobitých bytů v projektu',11)
link('Architektonický koncept / Ateliér Jakub Jaroš',M,70,SOURCES[1][1])
finish()

# 03 - Current construction status is not invented.
page('Proměna bývalé školy','Charakter zůstává.\nDomov získává nový rozměr.','rekonstrukce')
para(RECONSTRUCTION,M,673,CW,11.5)
image('house',M,263,CW,329)
text(M,248,'Uliční fasáda / skutečná fotografie domu',8.5,'Sans',MUTED)
para('Historická architektura je výchozím bodem návrhu. Konkrétní technické řešení, aktuální stav rekonstrukce a standard dodávky projdete s kontaktem projektu.',M,210,CW,11)
button('Zjistit standard a aktuální stav',M,83,300,'mailto:'+EMAIL+'?subject=Standard%20a%20rekonstrukce')
finish()

# 04 - Garden proposal and its scope.
page('02 / Zahrada','Za dveřmi město.\nZa domem zahrada.','zahrada',dark=True)
para(GARDEN,M,675,CW,11.5,PAPER)
rect(M,243,CW,336,'#ffffff');image('garden.png',M+15,258,CW-30,306)
text(M,226,'Krajinářský návrh / původní projektová brožura',8.5,'Sans',LIGHT)
para('Ranní káva. Chvíle s knihou. Návrat domů. Návrh zahradního prostředí přidává bydlení další rozměr.',M,195,CW,12,PAPER)
para(GARDEN_NOTE,M,124,CW,9.5,LIGHT)
finish()

# 05 - Factual city guide, without made-up walking distances.
page('04 / Louny','Malé město.\nVelký prostor pro život.','louny')
para('Večer v divadle. Ráno u řeky. Umění, plavání a káva po cestě. Louny mají vlastní kulturní život a historické centrum.',M,675,CW,11.5)
for i,(number,name,description,url,query) in enumerate(PLACES):
 x=M+(i%2)*267;top=582-(i//2)*147;line(top+11,x,x+244)
 text(x,top-11,number,8,'Sans',BRASS)
 bottom=para(escape(name),x,top-24,240,18,INK,'Serif',22)
 para(description,x,bottom-13,239,10)
 link('Prohlédnout místo',x,top-108,url,8.5)
para('Školy, školky a městské služby: aktuální přehled města. Výlety do okolí: Ohře, Raná a Oblík. Mapové odkazy na webu vedou na konkrétní místa ve městě.',M,116,CW,9.5,MUTED)
link('Město a služby',M,66,'https://www.mulouny.cz/');link('Trasy v okolí',230,66,SOURCES[8][1])
finish()

# 06 - The Prague story is an interpretation of a documented transport update.
page('05 / Praha a doprava','Praha blíž.\nVáš život po svém.','doprava')
para('Zlepšující se spojení otevírá prostor pro život mezi městem, prací a domovem. Hlavní hodnotou Loun přitom zůstávají Louny samotné.',M,675,CW,11.5)
events=[('2023','Obchvat Loun','Dálniční rozšíření v provozu od září.'),('2024','Chlumčany','Navazující úsek zprovozněný v červnu.'),('2026','Výstavba pokračuje','Od září provoz na části nového pásu u Knovíze, v této etapě 1+1.'),('2027 / plán','Tři středočeské úseky','Knovíz-Slaný-západ, Slaný-západ-Kutrovice a Kutrovice-Panenský Týnec. Plán se může změnit.')]
for i,(date,title,description) in enumerate(events):
 top=569-i*108;text(M,top,date,9,'Sans',BRASS);text(M,top-26,title,18,'Serif');para(description,M,top-40,234,10.5)
rect(315,230,238,362,INK);text(336,550,'PID / VEŘEJNÁ DOPRAVA',8,'Sans','#c7ad76');text(336,476,'389',60,'Serif','#c7ad76')
para('Louny<br/>Slaný<br/>Praha, Nádraží Veleslavín',336,444,194,20,PAPER,'Serif',28)
para(PID_TEXT,336,331,195,9.5,PAPER)
link('Aktuální jízdní řády',336,248,SOURCES[4][1],9,'#c7ad76')
para('Stav ověřen '+VERIFIED+'. „Praha blíž“ vyjadřuje vývoj dopravního spojení. Doba cesty závisí na konkrétním spoji, cíli a provozu.',M,155,CW,9,MUTED)
link('Přehled D7',M,93,SOURCES[2][1]);link('Zpráva ŘSD / 1. 9. 2026',212,93,SOURCES[3][1])
finish()

# 07 - A linked index for comparison.
page('03 / Vyberte svůj byt','Šest podob domova.','vyber')
para('Od historických oken druhého podlaží po osobité podkroví. Vyberte si dispozici a prostor pro svůj život.',M,703,CW,11)
for i,u in enumerate(UNITS):
 a,floor,layout,total,*_=u;x=M+(i%2)*267;y=465-(i//2)*183
 rect(x,y,244,165,'#ffffff');text(x+14,y+127,a,29,'Serif');text(x+60,y+141,layout.replace(' + ','+'),12,'Serif');text(x+60,y+121,total+' m²',11,'Sans')
 image('archviz-'+a.lower()+'.webp',x+14,y+29,216,77)
 text(x+14,y+12,floor,8,'Sans',MUTED)
 c.linkRect('Byt '+a,'byt-'+a.lower(),(x,y,x+244,y+165),relative=0,thickness=0)
para(AREA_NOTE+' Cenu a dostupnost získáte u kontaktu projektu.',M,92,CW,8.5,MUTED)
finish()

for u in UNITS[:3]:unit_visual(u);unit_plan(u)

# 14 - Attic concept applies to the project, without assigning generic views to a unit.
page('Podkrovní koncept','Pod střechou.\nNad běžným.','podkrovi',dark=True)
para(ATTIC,M,675,CW,11.5,PAPER)
image('06-loft.webp',M,269,CW,314)
text(M,250,'Podkrovní koncept / vizualizace, návrh vybavení',8.5,'Sans',LIGHT)
image('07-loft-kitchen.webp',M,74,246,155);image('08-loft-dining.webp',307,74,246,155)
finish()
for u in UNITS[3:]:unit_visual(u);unit_plan(u)

# 21-23 - Exact, losslessly embedded original floor drawings.
for title,name,description,key in [
 ('2. nadzemní podlaží','plan-second','Byty A, B a C v původní projektové dispozici.','podlazi-2'),
 ('Podkroví','plan-attic','Byty D, E a F v původní projektové dispozici.','podlazi-podkrovi'),
 ('Loftová úroveň','plan-loft','Loftová patra bytů D a E.','podlazi-loft')]:
 page('Dům v souvislostech / Projektový výkres',title,key)
 para(description,M,706,CW,11)
 rect(M,202,CW,449,'#ffffff');image(name+'.png',M+12,215,CW-24,422)
 para('Původní projektový výkres. Dispozice a čísla místností zůstávají beze změn.',M,166,CW,10,MUTED)
 link('Otevřít výkres v plném rozlišení',M,98,SITE_URL+'/assets/'+name+'.png')
 finish()

# 24 - Site context.
page('Zahrada / Projektová situace','Dům a jeho okolí.','situace')
para('Původní situační návrh ukazuje návaznost domu na zahradní prostředí a okolní zástavbu.',M,706,CW,11.5)
rect(M,267,CW,356,'#ffffff');image('site.png',M+12,279,CW-24,332)
para(GARDEN_NOTE,M,233,CW,11)
para('U zahrady, terasy a parkování projděte současné provedení a způsob užívání společně s nabídkou konkrétního bytu.',M,168,CW,10.5)
link('Prohlédnout projektovou situaci',M,88,SITE_URL+'/assets/site.png')
finish()

# 25 - Transparent purchase journey.
page('06 / Standard a další kroky','Podrobnosti rozhodují.','standard')
para('Vybrat byt. Získat nabídku a prohlídku. Projít standard a dokumentaci. Konkrétní podmínky navazujících kroků určuje individuální nabídka.',M,704,CW,11.5)
y=621
for question,answer in FAQ:
 line(y+5);bottom=para(question,M,y-8,CW,13,INK,'Bold',19);y=para(answer,M,bottom-12,CW,10.5)-29
button('Domluvit prohlídku',M,78,243,'mailto:'+EMAIL+'?subject=Prohlidka%20Viladum')
finish()

# 26 - Reader-facing source notes and dates.
page('Zdroje a platnost informací','Důvěra je v podrobnostech.','zdroje')
para('Místní a dopravní údaje ověřeny '+VERIFIED+'. Dispozice a výměry pocházejí z původní projektové brožury. Architektura a zahrada jsou popsané v rozsahu doloženého návrhu.',M,704,CW,10.5)
y=620
for label,url in SOURCES:
 line(y-12);link(label,M,y,url,10,INK);y-=29
para('Rozpočet Loun pro rok 2026 počítá s téměř 140 mil. Kč do výstavby. Jde o plán. Triangle uvádí 5 207 zaměstnanců k 31. 12. 2025; tento údaj dokládá regionální pracovní zázemí.',M,147,CW,9,MUTED)
para('Vizualizace nejsou fotografiemi dokončených interiérů. Rozsah dodávky, aktuální stav a práva užívání potvrdí kontakt projektu.',M,91,CW,8.5,MUTED)
finish()

# 27 - Contact and QR for the requested fortress deployment URL.
page('07 / Váš další krok','Tenhle příběh\nmůže být váš.','kontakt',dark=True)
para('Vyberte si byt a domluvte prohlídku. Projdeme s vámi dispozici, aktuální nabídku i důležité podrobnosti.',M,663,CW,12,PAPER)
text(M,552,'Jan Čáka',27,'Serif',PAPER);text(M,524,'Kontakt projektu',9,'Sans',LIGHT)
link(PHONE,M,465,'tel:+420774320438',26,PAPER);link(EMAIL,M,422,'mailto:'+EMAIL,25,PAPER)
link(PROJECT_ADDRESS,M,390,'https://mapy.com/cs/zakladni?q=Osvoboditel%C5%AF%20497%2C%20Louny',12,PAPER)
button('Domluvit prohlídku',M,335,250,'mailto:'+EMAIL+'?subject=Prohlidka%20Viladum',False)
qr=QrCodeWidget(SITE_URL);x0,y0,x1,y1=qr.getBounds();size=118
rect(421,201,132,132,'#ffffff');drawing=Drawing(size,size,transform=[size/(x1-x0),0,0,size/(y1-y0),0,0]);drawing.add(qr);renderPDF.draw(drawing,c,428,208)
text(M,274,'Online prezentace / bez přihlášení',11,'Sans',PAPER)
link('Otevřít online prezentaci',M,242,SITE_URL,11,'#c7ad76')
para(AREA_NOTE+' Aktuální nabídku, stav rekonstrukce a podmínky užívání společných částí potvrdí kontakt projektu.',M,167,CW,9,LIGHT)
text(M,77,'ŘÍJEN 2026 / VILADŮM V ZAHRADÁCH',8.5,'Sans','#c7ad76')
finish()
c.save()
(ROOT/'pdf-layout-metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2))
print(str(OUT),page_number,'pages',OUT.stat().st_size,'bytes')
