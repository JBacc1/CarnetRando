#Version 1.0
#Code sous licence FTWPL

#À faire : 
# - introduire Class pour les cadres.
# - vérifier les données de page : inversion du format, tailles_utiles et page négatives.
#2.91902075410828,45.6838272387137,3.0231216105798,45.8750921072418
#Pré-supposé : (hauteur/largeur(page)-1)*(hauteur/largeur(page sans les marges)-1)>0 (si page en paysage, reste paysage après déduction des marges, idem portrait)
import os.path
from os import makedirs
import time
import sys 
import csv
import string
import math
import urllib.request
import configparser
import argparse
from subprocess import Popen

RTerre=6378.0
entete_cadre=("num","cx","cy","miny","minx","maxy","maxx","mapscale","portrait","format","DPI","description")
inifilename='CarnetRando.ini'
ressfilename='ressources.ini'

def eval_portrait(st):
	if st.lower() in ['1', 'true', 't', 'y', 'yes', 'portrait', 'p','por','port','portr']:
		return 'portrait'
	elif st.lower() in ['0', 'false', 'f', 'n', 'no', 'landscape', 'l','landsc','ldscp','paysage','pays','pays.']:
		return 'landscape'
	elif st.lower()[0:1]=='l':
		return 'landscape'
	else:
		print('Incertitude sur l\'orientation désignée par "'+st.lower()+'". Retourné "portrait" par défaut')
		return 'portrait'
def is_portrait(st):
	return (eval_portrait(st)=='portrait')

def eval_format_custom(chaine,bool_portrait):
	a=[float(x)for x in ((str.replace(chaine,",",".")).split("_")[1:3])]
	if bool_portrait:
		format=(min(a),max(a))
	else:
		format=(max(a),min(a))
	return format
def is_paper_custom(format):
	try: 
		eval_format_custom(format,True)
		return True
	except:
		return False	
def formatA(taille,bool_portrait):
# largeur, hauteur
	p=bool_portrait
	if taille=="A3":
		if p:
			format=(29.7,42)
		else:
			format=(42,29.7)
	elif taille=="A4":
		if p:
			format=(21,29.7)
		else:
			format=(29.7,21)
	elif taille=="A5":
		if p:
			format=(14.8,21)
		else:
			format=(21,14.8)
	elif taille=="A6":
		if p:
			format=(10.5,14.8)
		else:
			format=(14.8,10.5)
	elif str.lower(taille)[:6]=="custom":
		try:
			format=eval_format_custom(taille,p)
		except: 
			print("Le format « "+taille+" » n'a pas été reconnu. Le format A5 sera utilisé par défaut.")
			format=formatA("A5",p)
	else:
		print("Le format indiqué dans le fichier .ini n'a pas été reconnu ("+taille+"). Utilisé A5 par défaut")
		format=formatA("A5",p)
	return format

def str2latex(txt):
	a=txt
	a=a.strip()
	a=a.replace("\\","\\textbackslash ")
	a=a.replace('_','\\_')
	return a

def haversin(ax, ay, bx, by):
	a= (math.sin((math.radians(ay)-math.radians(by))/2)**2 + (math.cos(math.radians(ay)))*(math.cos(math.radians(by)))*(math.sin((math.radians(ax)-math.radians(bx))/2))**2)
	return 2*math.atan2(math.sqrt(a),math.sqrt(1-a))*RTerre

def rename(old,new):
	if os.path.isfile(new):
		print('Le fichier '+new+' est déjà présent. Suppression')
		os.remove(new)
	os.rename(old,new)

def is_assemblage_portrait(osmfile,w,h):
	with open(osmfile,'r',encoding='utf-8') as assemblage:
		for ligne in assemblage:
			if str.lstrip(ligne,string.whitespace)[:7]=='<bounds':
				ligne=str.lstrip(ligne,string.whitespace)
				break
#  <bounds minlat='47.8029884820485' minlon='6.95898602589246' maxlat='48.1774219012266' maxlon='7.17170655006768' />
	minlat=float(ligne.partition("minlat='")[2].partition("'")[0])
	minlon=float(ligne.partition("minlon='")[2].partition("'")[0])
	maxlat=float(ligne.partition("maxlat='")[2].partition("'")[0])
	maxlon=float(ligne.partition("maxlon='")[2].partition("'")[0])
	deltax=haversin(minlon,(minlat+maxlat)/2,maxlon,(minlat+maxlat)/2)
	deltay=haversin((minlon+maxlon)/2,minlat,(minlon+maxlon)/2,maxlat)
	if deltax/deltay<w/h:
		format="portrait"
	else:
		format="landscape"
	return format

def download_data():
	if ini['DATA']['osmdata_downloadurl']!='':
		print("Téléchargement des données depuis l'adresse fournie :",ini['DATA']['osmdata_downloadurl'])
		print("Telechargement démarré")
		openurl = urllib.request.urlretrieve(ini['DATA']['osmdata_downloadurl'],ini['PATH']['osmfiles']+"/"+ini['DATA']['osmdata'])
		print ("Telechargement OK")
	else:
		print("Pas de lien de téléchargement fourni.")
		lien="http://download.geofabrik.de/europe/france/"+ini['DATA']['osmdata']
		print("Essai avec :",lien)
		try:
			openurl = urllib.request.urlretrieve(lien,ini['PATH']['osmfiles']+"/"+ini['DATA']['osmdata'])
			print ("Telechargement OK")
		except:
			fr=""
			while not (fr=="y" or fr=="n" or fr=="Y" or fr=="N"):
				fr=input("L'opération a échoué. Voulez-vous télécharger le fichier France (>3Go) ? Le traitement des cadres sera plus long avec un fichier de cette taille.\nY/N")
			if fr=='n' or fr=="N":
				print("Merci de fournir un fichier de données ou un lien de téléchargement, et de renseigner le fichier "+inifilename+".")
				sys.exit()
			else:
				ini['DATA']['osmdata']="france-latest.osm.pbf"
				print("Démarrage du téléchargement depuis : http://download.geofabrik.de/europe/france-latest.osm.pbf.")
				openurl = urllib.request.urlretrieve("http://download.geofabrik.de/europe/france-latest.osm.pbf", ini['PATH']['osmfiles']+"/"+ini['DATA']['osmdata'])
				print ("Téléchargement OK")

def download_alsace_lorraine():
	print("Téléchargement des données depuis geofabrik.de")
	print("Telechargement d'alsace-latest.osm.pbf")
	urllib.request.urlretrieve("http://download.geofabrik.de/europe/france/alsace-latest.osm.pbf","alsace.osm.pbf")
	print ("Telechargement OK")
	print ("Telechargement de lorraine-latest.osm.pbf")
	urllib.request.urlretrieve("http://download.geofabrik.de/europe/france/lorraine-latest.osm.pbf","lorraine.osm.pbf")
	print ("Telechargement OK")

	popstr='C:/OSM/osmosis-latest/bin/osmosis.bat --read-pbf file="C:/OSM/CarnetRando/alsace.osm.pbf" --read-pbf file="C:/OSM/CarnetRando/lorraine.osm.pbf" --merge --write-pbf file="C:/OSM/CarnetRando/alsace_lorraine.osm.pbf"'
	print ("Rassemblement des fichiers alsace et lorraine avec Osmosis. Commande : \n"+popstr)
	pop=Popen(popstr)
	pop.wait()
	print ("Rassemblement OK")
def download_pyrenees():
	print("Téléchargement des données depuis geofabrik.de")
	print("Telechargement de spain-latest.osm.pbf")
	urllib.request.urlretrieve("http://download.geofabrik.de/europe/spain-latest.osm.pbf","spain.osm.pbf")
	print ("Telechargement OK")
	print ("Telechargement d'aquitaine-latest.osm.pbf")
	urllib.request.urlretrieve("http://download.geofabrik.de/europe/france/aquitaine-latest.osm.pbf","aquitaine.osm.pbf")
	print ("Telechargement OK")
	print ("Telechargement de midi-pyrenees-latest.osm.pbf")
	urllib.request.urlretrieve("http://download.geofabrik.de/europe/france/midi-pyrenees-latest.osm.pbf","midipyrenees.osm.pbf")
	print ("Telechargement OK")
	print ("Telechargement de languedoc-roussillon.osm.pbf")
	urllib.request.urlretrieve("http://download.geofabrik.de/europe/france/languedoc-roussillon-latest.osm.pbf","languedocroussillon.osm.pbf")
	print ("Telechargement OK")

	popstr='C:/OSM/osmosis-latest/bin/osmosis.bat --read-pbf file="C:/OSM/CarnetRando/languedocroussillon.osm.pbf" --read-pbf file="C:/OSM/CarnetRando/aquitaine.osm.pbf"  --read-pbf file="C:/OSM/CarnetRando/midipyrenees.osm.pbf" --read-pbf file="C:/OSM/CarnetRando/spain.osm.pbf" --merge --merge --merge --write-pbf file="C:/OSM/CarnetRando/gdpyreneestemp.osm.pbf"'
	print ("Rassemblement des fichiers avec Osmosis. Commande : \n"+popstr)
	pop=Popen(popstr)
	pop.wait()
	os.remove('midipyrenees.osm.pbf')
	os.remove('spain.osm.pbf')
	os.remove('aquitaine.osm.pbf')
	os.remove('languedocroussillon.osm.pbf')
	print ("Rassemblement OK")

	#minlat='42.40233419893856' minlon='-1.777559828603853' maxlat='43.37625648272529' maxlon='3.141854769210746'
	popstr='C:/OSM/osmosis-latest/bin/osmosis.bat --read-pbf file="C:/OSM/CarnetRando/gdpyreneestemp.osm.pbf" --bounding-box bottom='+str(42.35)+' left='+str(-1.80)+' top='+str(43.4)+' right='+str(3.2)+' completeWays=yes completeRelations=yes --write-pbf file="C:/OSM/CarnetRando/pyreneestemp.osm.pbf"'
	print ("Découpe du fichier avec Osmosis. Commande : \n"+popstr)
	pop=Popen(popstr)
	pop.wait()
	os.remove('gdpyreneestemp.osm.pbf')
	popstr='C:/OSM/osmosis-latest/bin/osmosis.bat --read-pbf file="C:/OSM/CarnetRando/pyreneestemp.osm.pbf" --bounding-box bottom='+str(41.85)+' left='+str(-2.30)+' top='+str(44.4)+' right='+str(4.2)+' --write-pbf file="C:/OSM/CarnetRando/pyrenees.osm.pbf"'
	print ("Découpe du fichier avec Osmosis. Commande : \n"+popstr)
	pop=Popen(popstr)
	pop.wait()
	os.remove('pyreneestemp.osm.pbf')
	print ("Découpe OK")
	
def load_cadres(csvfile):
	table_cadres={}
	ligne_ignoree=0
	print ("Ouverture du fichier "+csvfile)
	print ("Analyse du fichier")
	fc = open(csvfile,'r',newline='',encoding='utf-8')
	dialect = csv.Sniffer().sniff(fc.read(4096))
	fc.seek(0)
	has_header=csv.Sniffer().has_header(fc.read(4096))
	fc.seek(0)
	cadresreader=csv.reader(fc,dialect)
	if has_header:
		ligne=cadresreader.__next__()
		print ("Une ligne d'en-tête détectée et ignorée")

	for ligne in cadresreader:
		try:
			table_cadres[ligne[0]]=[float(ligne[1]),float(ligne[2]),float(ligne[3]),float(ligne[4]),float(ligne[5]),float(ligne[6]),float(ligne[7]),eval_portrait(ligne[8]),ligne[9],float(ligne[10]),ligne[11]]
		except:
			ligne_ignoree +=1
	
	i=0
	for ligne in table_cadres.keys():
#		print table_cadres[ligne]
		i+=1
	print ("Analyse réussie, "+str(i)+" cadres recensés, "+str(ligne_ignoree)+" ligne(s) ignorée(s) (hors en-tête)")
	fc.close()
	return table_cadres
def load_cadres_table(csvfile):
	table_cadres=[]
	ligne_ignoree=0
	print ("Ouverture du fichier "+csvfile)
	print ("Analyse du fichier")
	fc = open(csvfile,'r',newline='',encoding='utf-8')
	dialect = csv.Sniffer().sniff(fc.read(4096))
	fc.seek(0)
	has_header=csv.Sniffer().has_header(fc.read(4096))
	fc.seek(0)
	cadresreader=csv.reader(fc,dialect)
	if has_header:
		ligne=cadresreader.__next__()
		print ("Une ligne d'en-tête détectée et ignorée")

	for ligne in cadresreader:
		try:
			table_cadres.append([ligne[0],float(ligne[1]),float(ligne[2]),float(ligne[3]),float(ligne[4]),float(ligne[5]),float(ligne[6]),float(ligne[7]),eval_portrait(ligne[8]),ligne[9],float(ligne[10]),ligne[11]])
		except:
			ligne_ignoree +=1
	
	i=0
	for ligne in table_cadres:
#		print table_cadres[ligne]
		i+=1
	print ("Analyse réussie, "+str(i)+" cadres recensés, "+str(ligne_ignoree)+" ligne(s) ignorée(s) (hors en-tête)")
	fc.close()
	return table_cadres

def decoupe_osm(miny,minx,maxy,maxx,completerelations,infile,outfile):
	popstr=ress['RESSOURCES']['osmosis']+' --read-pbf file="'+infile+'" --bounding-box bottom='+str(miny)+' left='+str(minx)+' top='+str(maxy)+' right='+str(maxx)+' completeWays=yes completeRelations=yes --write-xml file="'+outfile+'"'
	if not completerelations:
		popstr=popstr.replace('completeRelations=yes ','')
	if infile[len(infile)-4:]=='.osm':
		popstr=popstr.replace('-read-pbf','-read-xml')
	if outfile[len(outfile)-4:]=='.pbf':
		popstr=popstr.replace('-write-xml','-write-pbf')
	print ("Decoupe avec Osmosis. Commande : \n"+popstr)
	pop=Popen(popstr)
	pop.wait()
	print ("Decoupe OK")
	
def cree_mscript(osmfile,cadre):
##gérer paysage
	print ("Génération du fichier de script pour le cadre")
	mscript=open(ini['PATH']['scripts']+'/'+str.replace(str.replace(osmfile,".osm",".mscript"),"decoupe","script"),'w')
	mscript.write('use-ruleset location="'+ress['RESSOURCES']['defaultmrules']+'"\n')
	mscript.write('apply-ruleset\n')
	mscript.write('set-setting name=map.decoration.grid value=false\n')
	mscript.write('set-setting name=map.decoration.attribution value=false\n')
	mscript.write('set-setting name=map.decoration.scale value=true\n')
	mscript.write('set-dem-source name='+ini['DATA']['elevation_source']+'\n')
	mscript.write('set-geo-bounds bounds='+str(cadre[entete_cadre.index("minx")-1]-0.002)+','+str(cadre[entete_cadre.index("miny")-1]-0.0015)+','+str(cadre[entete_cadre.index("maxx")-1]+0.002)+','+str(cadre[entete_cadre.index("maxy")-1]+0.0015)+'\n')
	mscript.write('generate-relief-igor\n')
	mscript.write('generate-relief-igor\n')
	mscript.write('generate-contours interval=10\n')
	mscript.write('load-source "'+localpath+str.replace(ini['PATH']['osmfiles'],"./","/")+'/'+osmfile+'"\n')
	if ini.getboolean('MAP','printgpx') and args.gpxfile!=None:
		if os.path.isfile(args.gpxfile):
			mscript.write('load-source "'+os.path.abspath(args.gpxfile).replace("\\","/")+'"\n')
	mscript.write('set-print-bounds-paper center='+str(cadre[entete_cadre.index("cx")-1])+','+str(cadre[entete_cadre.index("cy")-1]) +' map-scale='+str(cadre[entete_cadre.index("mapscale")-1])+'\n')
	mscript.write('set-paper orientation='+cadre[entete_cadre.index("portrait")-1]) #pas de \n ici !
	if not is_paper_custom(cadre[entete_cadre.index("format")-1]):
		mscript.write(' type='+cadre[entete_cadre.index("format")-1])
	else:
#		set-paper height=400 width=300 orientation=portrait
		loc_page=formatA(cadre[entete_cadre.index("format")-1],is_portrait(cadre[entete_cadre.index("portrait")-1]))
		mscript.write(' height='+str(min(loc_page)*10)+' width='+str(max(loc_page)*10)) ##Oui, le format custom est géré bizarrement par Maperitive. 
	if is_portrait(cadre[entete_cadre.index("portrait")-1])==ini.getboolean('PDF','pdf_portrait'):
		mscript.write(' margins='+str(float(ini['PAGE']['marginouter'])*10)+','+str(float(ini['PAGE']['margintop'])*10)+','+str(float(ini['PAGE']['margininner'])*10)+','+str(float(ini['PAGE']['marginbottom'])*10)+'\n')
	else:
		mscript.write(' margins='+str(float(ini['PAGE']['margintop'])*10)+','+str(float(ini['PAGE']['margininner'])*10)+','+str(float(ini['PAGE']['marginbottom'])*10)+','+str(float(ini['PAGE']['marginouter'])*10)+'\n')
	mscript.write('export-bitmap "'+localpath+str.replace(ini['PATH']['cartes'],"./","/")+'/'+str.replace(str.replace(osmfile,".osm",""),"decoupe_","")+'.png" DPI='+str(cadre[entete_cadre.index("DPI")-1])+'\n')
	mscript.write('set-setting name=map.decoration.attribution value=true\n')
	mscript.write('set-dem-source name=SRTMV3R3\n')
	if is_paper_custom(ini['PAGE']['format']):  #bug de Maperitive, n'aime pas qu'on referme la console avec un papier type=custom. 
		mscript.write('set-paper type=A5\n')
	mscript.close()
	print ("Génération OK")
	
def run_script(scriptfile):
	popstr=ress['RESSOURCES']['maperitiveconsole']+' '+localpath+str.replace(ini['PATH']['scripts'],"./","/")+'/'+scriptfile
	print ("Exécution du script pour génération de la carte. Commande :\n"+popstr)
	mapscr=Popen(popstr)
	mapscr.wait()
	print ("Génération OK")

def cree_osmfile_assemblage(assemblagefile,tc) :
   print ("Génération du fichier : "+assemblagefile)
   osmfile=open(assemblagefile,'w',encoding='utf-8')
   osmfile.write("<?xml version='1.0' encoding='UTF-8'?>\n")
   osmfile.write("<osm version='0.6' upload='false' generator='JOSM'>\n")

   minminx=300.0
   maxmaxx=-300.0
   minminy=300.0
   maxmaxy=-300.0
   for nom_ligne in tc.keys():
      ligne=tc[nom_ligne]
      minx=(ligne[entete_cadre.index("minx")-1])
      miny=((ligne[entete_cadre.index("miny")-1]))
      maxx=(ligne[entete_cadre.index("maxx")-1])
      maxy=((ligne[entete_cadre.index("maxy")-1]))
      minminx=min(minx,minminx)
      minminy=min(miny,minminy)
      maxmaxx=max(maxx,maxmaxx)
      maxmaxy=max(maxy,maxmaxy)
   osmfile.write("  <bounds minlat='"+str(minminy)+"' minlon='"+str(minminx)+"' maxlat='"+str(maxmaxy)+"' maxlon='"+str(maxmaxx)+"' />\n")
   
   nid=-20070
   for nom_ligne in tc.keys():
      ligne=tc[nom_ligne]
      minx=str(ligne[entete_cadre.index("minx")-1])
      miny=str((ligne[entete_cadre.index("miny")-1]))
      maxx=str(ligne[entete_cadre.index("maxx")-1])
      maxy=str((ligne[entete_cadre.index("maxy")-1]))

      osmfile.write("  <node id='"+str(nid)+"' action='modify' visible='true' lat='"+miny+"' lon='"+minx+"' />\n")
      nid +=1
      osmfile.write("  <node id='"+str(nid)+"' action='modify' visible='true' lat='"+maxy+"' lon='"+minx+"' />\n")
      nid +=1
      osmfile.write("  <node id='"+str(nid)+"' action='modify' visible='true' lat='"+maxy+"' lon='"+maxx+"' />\n")
      nid +=1
      osmfile.write("  <node id='"+str(nid)+"' action='modify' visible='true' lat='"+miny+"' lon='"+maxx+"' />\n")
      nid +=1

   wid=nid
   nid=-20070
   for nom_ligne in tc.keys():
     ligne=tc[nom_ligne]
     osmfile.write("  <way id='"+str(wid)+"' action='modify' visible='true'>\n")
     osmfile.write("    <nd ref='"+str(nid)+"' />\n")
     osmfile.write("    <nd ref='"+str(nid+1)+"' />\n")
     osmfile.write("    <nd ref='"+str(nid+2)+"' />\n")
     osmfile.write("    <nd ref='"+str(nid+3)+"' />\n")
     osmfile.write("    <nd ref='"+str(nid)+"' />\n")
     osmfile.write("    <tag k='ref' v='"+str.replace(nom_ligne,"_"," ")+"' />\n")
     osmfile.write("    <tag k='name' v='"+str.replace((ligne[entete_cadre.index("description")-1]),"'","&apos;")+"' />\n")
     osmfile.write("    <tag k='rendu' v='cadre' />\n")
     osmfile.write("  </way>\n")
 
     wid +=1
     nid +=4

   osmfile.write("</osm>\n")
   osmfile.close()
   print ("Génération OK")

def cree_mscript_assemblage(scriptname,tc):
	print ("Génération du fichier de script pour l'assemblage")
	mscript=open(ini['PATH']['scripts']+'/'+scriptname+".mscript",'w')
	mscript.write('use-ruleset location="'+ress['RESSOURCES']['assemblagemrules']+'"\n')
	mscript.write('apply-ruleset\n')
	mscript.write('set-setting name=map.decoration.grid value=false\n')
	mscript.write('set-setting name=map.decoration.attribution value=false\n')
	mscript.write('set-setting name=map.decoration.scale value=false\n')
	mscript.write('set-dem-source name='+ini['DATA']['elevation_source']+'\n')
	
	minminx=300.0
	maxmaxx=-300.0
	minminy=300.0
	maxmaxy=-300.0
	for nom_ligne in tc.keys():
	  ligne=tc[nom_ligne]
	  minx=(ligne[entete_cadre.index("minx")-1])
	  miny=((ligne[entete_cadre.index("miny")-1]))
	  maxx=(ligne[entete_cadre.index("maxx")-1])
	  maxy=((ligne[entete_cadre.index("maxy")-1]))
	  minminx=min(minx,minminx)
	  minminy=min(miny,minminy)
	  maxmaxx=max(maxx,maxmaxx)
	  maxmaxy=max(maxy,maxmaxy)

	mscript.write('set-geo-bounds bounds='+str(minminx-0.005-float(ini['ASSEMBLAGE']['assemblage_leftmargin']))+','+str(minminy-0.005-float(ini['ASSEMBLAGE']['assemblage_bottommargin']))+','+str(maxmaxx+0.005+float(ini['ASSEMBLAGE']['assemblage_rightmargin']))+','+str(maxmaxy+0.005+float(ini['ASSEMBLAGE']['assemblage_topmargin']))+'\n')
	mscript.write('set-print-bounds-geo bounds='+str(minminx-float(ini['ASSEMBLAGE']['assemblage_leftmargin']))+','+str(minminy-float(ini['ASSEMBLAGE']['assemblage_bottommargin']))+','+str(maxmaxx+float(ini['ASSEMBLAGE']['assemblage_rightmargin']))+','+str(maxmaxy+float(ini['ASSEMBLAGE']['assemblage_topmargin']))+'\n')
	if ini.getboolean('ASSEMBLAGE','printshading_onassemblage'):
		mscript.write('generate-relief-igor\n')
		mscript.write('generate-relief-igor\n')
	mscript.write('load-source "'+localpath+str.replace(ini['FILES']['assemblageosm'],"./","/")+'"\n')
	if ini.getboolean('ASSEMBLAGE','printgpx_onassemblage') and args.gpxfile!=None:
		if os.path.isfile(args.gpxfile):
			mscript.write('load-source "'+os.path.abspath(args.gpxfile).replace("\\","/")+'"\n')
		else:
			print('Le fichier gpx spécifié « '+args.gpxfile+" » n'a pas été trouvé.")
	mscript.write('export-bitmap "'+localpath+str.replace(ini['PATH']['cartes'],'./','/')+'/assemblage.png" DPI='+str(int(ini['ASSEMBLAGE']['dpi_assemblage']))+' map-scale='+str(ini['ASSEMBLAGE']['assemblage_mapscale'])+'\n')
	mscript.write('set-setting name=map.decoration.scale value=true\n')
	mscript.write('set-dem-source name=SRTMV3R3\n')
	
	mscript.close()
	print ("Génération OK")

def gpx2cadres(gpxfile,taille_utile_km_gd,taille_utile_km_pt):
	"Découpe les enveloppes, non normalisées aux proportions de la feuille. Pas de point commun par cadre (rattrape certaines erreurs sur les traces gpx mal conditionnées)."
	import gpxpy
	format=""
	if ini.getboolean('MAP','forceportrait') or args.forceportrait:
		format="portrait"
	if ini.getboolean('MAP','forcelandscape') or args.forcelandscape:
		format="landscape"
	cadre=[200,100,-200,-100]
	cadretemp=cadre[:]  #xm ym xM yM
	liste_cadres=[]
	print()
	print("Analyse du fichier GPX : ",gpxfile)
	print('Distances maximales autorisées par cadre :\nGrande dimension : '+str(round(taille_utile_km_gd,4))+'km\nPetite dimension : '+str(round(taille_utile_km_pt,4))+'km')
	gpx_file = open(gpxfile, 'r')
	gpx = gpxpy.parse(gpx_file)
	for track in gpx.tracks:
		for segment in track.segments:
			for point in segment.points:
				if point.latitude<cadre[1]:
					cadretemp[1]=point.latitude
				if point.latitude>cadre[3]:
					cadretemp[3]=point.latitude
				if point.longitude<cadre[0]:
					cadretemp[0]=point.longitude
				if point.longitude>cadre[2]:
					cadretemp[2]=point.longitude
				DeltaX_km=haversin(cadretemp[0],(cadretemp[1]+cadretemp[3])/2,cadretemp[2],(cadretemp[1]+cadretemp[3])/2)
				DeltaY_km=haversin((cadretemp[0]+cadretemp[2])/2,cadretemp[1],(cadretemp[0]+cadretemp[2])/2,cadretemp[3])
				if (DeltaX_km-taille_utile_km_pt>0 or DeltaY_km-taille_utile_km_gd>0)and (format==""):
					format="landscape"
				if (DeltaX_km-taille_utile_km_gd>0 or DeltaY_km-taille_utile_km_pt>0)and (format==""):
					format="portrait"
				if ((format=="portrait" and (DeltaX_km-taille_utile_km_pt>0 or DeltaY_km-taille_utile_km_gd>0))or(format=="landscape" and(DeltaX_km-taille_utile_km_gd>0 or DeltaY_km-taille_utile_km_pt>0))):
					cadre.append(format)
					print(cadre)
					liste_cadres.append(cadre)
					cadretemp=[point.longitude,point.latitude,point.longitude,point.latitude]
					format=""
					if ini.getboolean('MAP','forceportrait') or args.forceportrait:
						format="portrait"
					if ini.getboolean('MAP','forcelandscape') or args.forcelandscape:
						format="landscape"
				cadre=cadretemp[:]
	if format=="":
		format="portrait"
	cadre.append(format)
	print(cadre)
	liste_cadres.append(cadre)
	print("Analyse terminée : ",len(liste_cadres)," cadres créés." )
	return liste_cadres

def pavage2cadres(bounds,taille_utile_km_gd,taille_utile_km_pt,mapscale):
	if args.forcelandscape:
		taille_utile_km_gd,taille_utile_km_pt=taille_utile_km_pt,taille_utile_km_gd
	print("\nDémarrage du pavage")
	cadres=[]
	cadre=[]
	cy=[]
	cx=[]
	format='portrait'
	if ini.getboolean('MAP','forcelandscape') or args.forcelandscape:
		format="landscape"

	deltay=0.000000001/mapscale
	top=bounds[3]
	while top>bounds[1]:
		bottom=top-deltay
		#Méthode hyper crado suffisante de recherche de racine pour pas installer et charger le gros paquet scipy.optimize.brentq 
		#Ça reste hyper super rapide avec une erreur de l'ordre de 1 pour 1000
		while haversin(bounds[0],top,bounds[0],bottom)<taille_utile_km_gd:
			bottom -=deltay
		cy.append((top+bottom)/2)
		top=bottom
	#Post-traitement pour centrage en hauteur.
	decalage=(bounds[1]-bottom)/2
	cy[:]=[a+decalage for a in cy]
	print('Nombre de cadres en hauteur : '+str(len(cy)))
	print(cy)
	deltax=0.000000001/mapscale
	left=bounds[0]
	cbottom = cy[len(cy)-1]
	while left<bounds[2]:
		right=left+deltax
		#Méthode hyper crado suffisante de recherche de racine pour pas installer et charger le gros paquet scipy.optimize.brentq 
		#Ça reste hyper super rapide.
		while haversin(left,cbottom,right,cbottom)<taille_utile_km_pt:
			right += deltax
		cx.append((left+right)/2)
		left=right
	#Post-traitement pour décalage horizontal.
	decalage=(right-bounds[2])/2
	cx[:] = [a-decalage for a in cx]
	print('Nombre de cadres en largeur : '+str(len(cx)))
	print(cx)

	if not args.atlascolumn:
		ytext='A'
		xtext=1
		for y in cy:
			for x in cx:
				cadre.extend([x,y,x,y])
				cadre.append(format)
				cadres.append(cadre)				
				cadre.append(ytext+str(xtext))
				xtext +=1
				cadre=[]
			ytext=chr(ord(ytext)+1)
			xtext=1
	else:
		ytext=1
		xtext='A'
		for x in cx:
			for y in cy:
				cadre.extend([x,y,x,y])
				cadre.append(format)
				cadres.append(cadre)				
				cadre.append(xtext+str(ytext))
				ytext +=1
				cadre=[]
			xtext=chr(ord(xtext)+1)
			ytext=1
	print("Pavage déterminé par "+str(len(cadres))+" cadres")
	if len(cadres)==0:
		print('Aucun cadre placé. Vérifiez vos coordonnées.')
		sys.exit()
	return cadres
	
def cadres2csvfile(liste_cadres,csvfile,page_km_gd,page_km_pt,mapscale):
	print("Enregistrement des cadres dans le fichier : "+csvfile)
#	entete_cadre=("num","cx","cy","miny","minx","maxy","maxx","mapscale","portrait","format","DPI","description")
	fw = open(csvfile,'w', newline='',encoding='utf-8')
	fw.write("Référence de cadre,Centre X,Centre Y,miny,minx,maxy,maxx,MapScale,Portrait,Format,DPI,Description\n")
	writer=csv.writer(fw)
	i=1
	for cadre in liste_cadres:
		try:
			wrow=[cadre[5]]
		except:
			wrow=[str(i)]
		wrow.extend([(cadre[0]+cadre[2])/2,((cadre[1]+cadre[3])/2)])
		if is_portrait(cadre[4]):
			wrow.append(math.degrees(math.asin(math.sin(math.radians(wrow[2]))*math.cos(page_km_gd/2.0/RTerre) - math.cos(math.radians(wrow[2]))*math.sin(page_km_gd/2.0/RTerre))))
			wrow.append(wrow[1]-math.degrees(math.atan2(1*math.sin((page_km_pt/2.0/RTerre))*math.cos(math.radians(wrow[2])),math.cos((page_km_pt/2.0/RTerre))-math.sin(math.radians(wrow[2]))**2)))
			wrow.append(math.degrees(math.asin(math.sin(math.radians(wrow[2]))*math.cos(page_km_gd/2.0/RTerre) + math.cos(math.radians(wrow[2]))*math.sin(page_km_gd/2.0/RTerre))))
			wrow.append(wrow[1]+math.degrees(math.atan2(1*math.sin((page_km_pt/2.0/RTerre))*math.cos(math.radians(wrow[2])),math.cos((page_km_pt/2.0/RTerre))-math.sin(math.radians(wrow[2]))**2)))
		else:
			wrow.append(math.degrees(math.asin(math.sin(math.radians(wrow[2]))*math.cos(page_km_pt/2.0/RTerre) - math.cos(math.radians(wrow[2]))*math.sin(page_km_pt/2.0/RTerre))))
			wrow.append(wrow[1]-math.degrees(math.atan2(1*math.sin((page_km_gd/2.0/RTerre))*math.cos(math.radians(wrow[2])),math.cos((page_km_gd/2.0/RTerre))-math.sin(math.radians(wrow[2]))**2)))
			wrow.append(math.degrees(math.asin(math.sin(math.radians(wrow[2]))*math.cos(page_km_pt/2.0/RTerre) + math.cos(math.radians(wrow[2]))*math.sin(page_km_pt/2.0/RTerre))))
			wrow.append(wrow[1]+math.degrees(math.atan2(1*math.sin((page_km_gd/2.0/RTerre))*math.cos(math.radians(wrow[2])),math.cos((page_km_gd/2.0/RTerre))-math.sin(math.radians(wrow[2]))**2)))
		wrow.append(round(1.0/mapscale))
		wrow.append(cadre[4])
		wrow.append(ini['PAGE']['format'])
		wrow.append(int(ini['MAP']['dpi_map']))
		try:
			wrow.append(cadre[5])
		except:
			wrow.append(str(i))
		writer.writerow(wrow)
		i += 1
	fw.close()
	print("Enregistrement OK")
	
def import_cadres(infile,outfile):
	print("Importation des cadres du fichier « "+infile+" » vers le fichier « "+outfile+" »")
	fw = open(outfile,'w', newline='', encoding='utf-8')
	fw.write("Référence de cadre,Centre X,Centre Y,miny,minx,maxy,maxx,MapScale,Portrait,Format,DPI,Description\n")
	writer=csv.writer(fw)
	
	inread = open(infile,'r',newline='',encoding='utf-8')
	dialect = csv.Sniffer().sniff(inread.read(4096))
	inread.seek(0)
	has_header=csv.Sniffer().has_header(inread.read(4096))
	inread.seek(0)
	csvinreader=csv.reader(inread,dialect)
	if has_header:
		ligne=csvinreader.__next__()
		print ("Une ligne d'en-tête détectée et ignorée")
	ligne_ignoree=0
	ligne_non_ignoree=0

#	entete_cadre=("num","cx","cy","miny","minx","maxy","maxx","mapscale","portrait","format","DPI")
#	import=Référence,Centre X,Centre Y,Scale,portrait/landscape,Format,DPI,Description
	for ligne in csvinreader:
		try:
			wrow=[ligne[0],(float(ligne[1])),(float(ligne[2]))]
			mapscale=1/float(ligne[3])
			PL=eval_portrait(ligne[4])
			page=formatA(ligne[5],PL=='portrait')
			if PL=='portrait':
				pageutile_cm_grand=page[1]-(float(ini['PAGE']['margintop'])+float(ini['PAGE']['marginbottom']))
				pageutile_cm_petit=page[0]-(float(ini['PAGE']['marginouter'])+float(ini['PAGE']['margininner']))
				page_km_pt=pageutile_cm_petit/mapscale*0.00001
				page_km_gd=pageutile_cm_grand/mapscale*0.00001
				wrow.append(math.degrees(math.asin(math.sin(math.radians(wrow[2]))*math.cos(page_km_gd/2.0/RTerre) - math.cos(math.radians(wrow[2]))*math.sin(page_km_gd/2.0/RTerre))))
				wrow.append(wrow[1]-math.degrees(math.atan2(1*math.sin((page_km_pt/2.0/RTerre))*math.cos(math.radians(wrow[2])),math.cos((page_km_pt/2.0/RTerre))-math.sin(math.radians(wrow[2]))**2)))
				wrow.append(math.degrees(math.asin(math.sin(math.radians(wrow[2]))*math.cos(page_km_gd/2.0/RTerre) + math.cos(math.radians(wrow[2]))*math.sin(page_km_gd/2.0/RTerre))))
				wrow.append(wrow[1]+math.degrees(math.atan2(1*math.sin((page_km_pt/2.0/RTerre))*math.cos(math.radians(wrow[2])),math.cos((page_km_pt/2.0/RTerre))-math.sin(math.radians(wrow[2]))**2)))
			else:
				pageutile_cm_grand=page[0]-(float(ini['PAGE']['marginouter'])+float(ini['PAGE']['margininner']))	
				pageutile_cm_petit=page[1]-(float(ini['PAGE']['margintop'])+float(ini['PAGE']['marginbottom']))
				page_km_pt=pageutile_cm_petit/mapscale*0.00001
				page_km_gd=pageutile_cm_grand/mapscale*0.00001
				wrow.append(math.degrees(math.asin(math.sin(math.radians(wrow[2]))*math.cos(page_km_pt/2.0/RTerre) - math.cos(math.radians(wrow[2]))*math.sin(page_km_pt/2.0/RTerre))))
				wrow.append(wrow[1]-math.degrees(math.atan2(1*math.sin((page_km_gd/2.0/RTerre))*math.cos(math.radians(wrow[2])),math.cos((page_km_gd/2.0/RTerre))-math.sin(math.radians(wrow[2]))**2)))
				wrow.append(math.degrees(math.asin(math.sin(math.radians(wrow[2]))*math.cos(page_km_pt/2.0/RTerre) + math.cos(math.radians(wrow[2]))*math.sin(page_km_pt/2.0/RTerre))))
				wrow.append(wrow[1]+math.degrees(math.atan2(1*math.sin((page_km_gd/2.0/RTerre))*math.cos(math.radians(wrow[2])),math.cos((page_km_gd/2.0/RTerre))-math.sin(math.radians(wrow[2]))**2)))
			wrow.append(str(float(ligne[3])))
			wrow.append(PL)
			wrow.append(ligne[5])
			wrow.append(ligne[6])
			wrow.append(ligne[7])
			writer.writerow(wrow)
			ligne_non_ignoree +=1
#			print(wrow)
		except:
			print('Une ligne mal conditionnée et ignorée :')
			print(ligne)
			ligne_ignoree +=1	
	inread.close()
	fw.close()
	print(str(ligne_non_ignoree)+" lignes importées et "+str(ligne_ignoree)+' lignes ignorees')
	print("Importation OK")
	
def export_cadres(infile,outfile):
	print("Export des cadres du fichier : "+infile+" vers le fichier : "+outfile)
	fw = open(outfile,'w', newline='', encoding='utf-8')
	fw.write("Référence,Centre X,Centre Y,Scale,portrait/landscape,Format,DPI,Description\n")
	writer=csv.writer(fw)
	
	inread = open(infile,'r',newline='',encoding='utf-8')
	dialect = csv.Sniffer().sniff(inread.read(4096))
	inread.seek(0)
	has_header=csv.Sniffer().has_header(inread.read(4096))
	inread.seek(0)
	csvinreader=csv.reader(inread,dialect)
	if has_header:
		ligne=csvinreader.__next__()
		print ("Une ligne d'en-tête détectée et ignorée")
	ligne_ignoree=0
	ligne_non_ignoree=0

	for ligne in csvinreader:
		try:
			wrow=[ligne[0],(float(ligne[1])),(float(ligne[2]))]
			wrow.append((float(ligne[entete_cadre.index("mapscale")])))
			wrow.append(eval_portrait(ligne[entete_cadre.index("portrait")]))
			wrow.append(ligne[entete_cadre.index("format")])
			wrow.append(int(ligne[entete_cadre.index("DPI")]))
			wrow.append(ligne[entete_cadre.index("description")])
			writer.writerow(wrow)
			ligne_non_ignoree +=1
			print(wrow)
		except:
			print('Une ligne mal conditionnée et ignorée :')
			print(ligne)
			ligne_ignoree +=1	
	inread.close()
	fw.close()
	print(str(ligne_non_ignoree)+" lignes exportées et "+str(ligne_ignoree)+' lignes ignorees')
	print("Exportation OK")
	
def script_global_cadres2cartes(filecadres):
	### Chargement des découpes à faire
	print()
	print("Démarrage de l'analyse des cadres")
#	entete_cadre=("num","cx","cy","miny","minx","maxy","maxx","mapscale","portrait","format","DPI")
	if not os.path.isfile(filecadres):
		print ("Le fichier de définition des cadres "+filecadres+" n'a pas été trouvé.\n"+"Le fichier de définition des cadres devrait contenir 8 colonnes : \n" + entete_cadre)
		print ("Soit Numéro du cadre, Centre de l'export en X, en Y, Cadre de découpe selon minY, minX, maxY, maxX, Échelle en 1/...\n"+"La première ligne peut être une en-tête.")
		print ("Arrêt")
		sys.exit()
	cadres=load_cadres(filecadres)

	### Génération de l'assemblage
	print()
	print("Démarrage du traitement de l'assemblage des cadres")
	cree_osmfile_assemblage(ini['FILES']['assemblageosm'],cadres)
	cree_mscript_assemblage("assemblage",cadres)
	run_script("assemblage"+".mscript")
	print ("Génération de l'assemblage OK")
	if args.assemblageonly:
		if os.path.isfile(ress['RESSOURCES']['pngreader']):
			Popen(ress['RESSOURCES']['pngreader']+localpath+str.replace(ini['PATH']['cartes'],'./','/')+'/assemblage.png')
		elif args.csvfile2pdf:
			return
		else:
			try:
				os.popen(localpath+str.replace(ini['PATH']['cartes'],'./','/')+'/assemblage.png')
			except:
				print('Pas de lecteur de fichier .png fourni')
		print('Option --assemblageonly')
		print('Terminé. Exécuté en '+str(round(time.time()-time_ini))+'s')	
		sys.exit()

	### Vérification de la présence du fichier à découper et téléchargement
	print()
	if ini.getboolean('BEHAVIOUR','forcedownload_osmdata') and ini['BEHAVIOUR']['osmdata_downloadurl']!='':
		download_data()
	elif not os.path.isfile(ini['PATH']['osmfiles']+"/"+ini['DATA']['osmdata']):
		print('Le fichier '+ini['PATH']['osmfiles']+"/"+ini['DATA']['osmdata']+' n\'est pas présent dans le dossier.')
		download_data()
	else:
		print('Le fichier '+ini['PATH']['osmfiles']+"/"+ini['DATA']['osmdata']+' est déjà présent.')

	### Pré-découpe des données OSM
	if ini.getboolean('OSM','precut1'):
		print()
		print('Prédécoupe des données OSM')
		if ini['DATA']['osmdata']=='data.osm.pbf':
			print("Le fichier de données OSM ne peut s'appeler data.osm.pbf, ce nom est réservé. Merci de choisir un autre nom de fichier et de renseigner le fichier .ini à DATA/osmdata")
			sys.exit()
		minminx=300.0
		maxmaxx=-300.0
		minminy=300.0
		maxmaxy=-300.0
		for nom_ligne in cadres.keys():
		  ligne=cadres[nom_ligne]
		  minx=(ligne[entete_cadre.index("minx")-1])
		  miny=((ligne[entete_cadre.index("miny")-1]))
		  maxx=(ligne[entete_cadre.index("maxx")-1])
		  maxy=((ligne[entete_cadre.index("maxy")-1]))
		  minminx=min(minx,minminx)
		  minminy=min(miny,minminy)
		  maxmaxx=max(maxx,maxmaxx)
		  maxmaxy=max(maxy,maxmaxy)
		decoupe_osm(minminy-float(ini['OSM']['precut1_verticalmargin']),minminx-float(ini['OSM']['precut1_horizontalmargin']),maxmaxy+float(ini['OSM']['precut1_verticalmargin']),maxmaxx+float(ini['OSM']['precut1_horizontalmargin']),ini.getboolean('OSM','precut1_completerelations'),ini['PATH']['osmfiles']+"/"+ini['DATA']['osmdata'],ini['PATH']['osmfiles']+'/'+"data.osm.pbf")
		if ini.getboolean('OSM','precut2'):
			rename(ini['PATH']['osmfiles']+'/'+"data.osm.pbf",ini['PATH']['osmfiles']+'/'+"data_temp.osm.pbf")
			decoupe_osm(minminy-float(ini['OSM']['precut2_verticalmargin']),minminx-float(ini['OSM']['precut2_horizontalmargin']),maxmaxy+float(ini['OSM']['precut2_verticalmargin']),maxmaxx+float(ini['OSM']['precut2_horizontalmargin']),ini.getboolean('OSM','precut2_completerelations'),ini['PATH']['osmfiles']+'/'+"data_temp.osm.pbf",ini['PATH']['osmfiles']+'/'+"data.osm.pbf")
			if ini.getboolean('BEHAVIOUR','remove_tempfiles'):
				os.remove(ini['PATH']['osmfiles']+'/'+"data_temp.osm.pbf")
		ini['DATA']['osmdata']='data.osm.pbf'
		print('Prédécoupe OK')

	### Génération des images
	print()
	print("Démarrage du traitement de chaque cadre.")
	i=len(cadres)
	for nom_cadre in cadres.keys():
		print ("Traitement du cadre : "+nom_cadre)
		cadre=cadres[nom_cadre]
	#	print cadre
		if ini.getboolean('OSM','cut1'):
			decoupe_osm(cadre[entete_cadre.index("miny")-1]-float(ini['OSM']['cut1_verticalmargin']),cadre[entete_cadre.index("minx")-1]-float(ini['OSM']['cut1_horizontalmargin']),cadre[entete_cadre.index("maxy")-1]+float(ini['OSM']['cut1_verticalmargin']),cadre[entete_cadre.index("maxx")-1]+float(ini['OSM']['cut1_horizontalmargin']),ini.getboolean('OSM','cut1_completerelations'),ini['PATH']['osmfiles']+"/"+ini['DATA']['osmdata'],localpath+str.replace(ini['PATH']['osmfiles'],"./","/")+'/'+"decoupe_"+nom_cadre+".osm")
			if ini.getboolean('OSM','cut2'):
				rename(localpath+str.replace(ini['PATH']['osmfiles'],"./","/")+'/'+"decoupe_"+nom_cadre+".osm",localpath+str.replace(ini['PATH']['osmfiles'],"./","/")+'/'+"decoupe_"+nom_cadre+"temp.osm")
				decoupe_osm(cadre[entete_cadre.index("miny")-1]-float(ini['OSM']['cut2_verticalmargin']),cadre[entete_cadre.index("minx")-1]-float(ini['OSM']['cut2_horizontalmargin']),cadre[entete_cadre.index("maxy")-1]+float(ini['OSM']['cut2_verticalmargin']),cadre[entete_cadre.index("maxx")-1]+float(ini['OSM']['cut2_horizontalmargin']),ini.getboolean('OSM','cut2_completerelations'),localpath+str.replace(ini['PATH']['osmfiles'],"./","/")+'/'+"decoupe_"+nom_cadre+"temp.osm",localpath+str.replace(ini['PATH']['osmfiles'],"./","/")+'/'+"decoupe_"+nom_cadre+".osm")
				if ini.getboolean('BEHAVIOUR','remove_tempfiles'):
					os.remove(localpath+str.replace(ini['PATH']['osmfiles'],"./","/")+'/'+"decoupe_"+nom_cadre+"temp.osm")
		else:
			popstr='C:/OSM/osmosis-latest/bin/osmosis.bat --read-pbf file='+ini['PATH']['osmfiles']+"/"+ini['DATA']['osmdata']+' --write-xml file="'+localpath+str.replace(ini['PATH']['osmfiles'],"./","/")+'/'+"decoupe_"+nom_cadre+'.osm"'
			if ini['DATA']['osmdata'][len(ini['DATA']['osmdata'])-4:]=='.osm':
				popstr=popstr.replace('-read-pbf','-read-xml')
			print ("Création du fichier de données. Commande : \n"+popstr)
			pop=Popen(popstr)
			pop.wait()
			print ("Création OK")
			
		cree_mscript("decoupe_"+nom_cadre+".osm",cadre)
		run_script("script_"+nom_cadre+".mscript")
		print ("Traitement du cadre OK")
		
		if ini.getboolean('BEHAVIOUR','remove_osmfiles'):
			os.remove(localpath+str.replace(ini['PATH']['osmfiles'],"./","/")+'/'+"decoupe_"+nom_cadre+".osm")

		i-=1
		print('Cadres restants à traiter : '+str(i)+'/'+str(len(cadres)))
		
	print ("Fin de la génération des cartes")

def script_global_pavage2cadres(bounds):
	page=formatA(ini['PAGE']['format'],ini.getboolean('PDF','pdf_portrait'))
	marges=(float(ini['PAGE']['marginouter'])+float(ini['PAGE']['margininner']),float(ini['PAGE']['margintop'])+float(ini['PAGE']['marginbottom']))
	recouvrement=[float(ini['MAP']['recouvrement_senslong']),float(ini['MAP']['recouvrement_senscourt'])]
	mapscale=1/float(ini['MAP']['mapscale'])
	
	taille_utile_km=((page[0]-marges[0]-recouvrement[0])/mapscale*0.00001,(page[1]-marges[1]-recouvrement[1])/mapscale*0.00001)
	print(page,marges,recouvrement,taille_utile_km)

	taille_utile_km_gd=max(taille_utile_km) #page-marge-recouvrement
	taille_utile_km_pt=min(taille_utile_km) ##$$ attention, cette ligne est fausse, si la longueur utile est inversée par rapport à la page.
	page_km=((page[0]-marges[0])/mapscale*0.00001,(page[1]-marges[1])/mapscale*0.00001)
	page_km_gd=max(page_km)
	page_km_pt=min(page_km)
	cadres2csvfile(pavage2cadres(bounds,taille_utile_km_gd,taille_utile_km_pt,mapscale),ini['FILES']['cadrescsv'],page_km_gd,page_km_pt,mapscale)
	
def script_global_gpx2cadres(gpxfile):
	if ini.getboolean('PDF','pdf_portrait'):
		(coordpt,coordgd)=(0,1)
	else:
		(coordpt,coordgd)=(1,0)
	page=formatA(ini['PAGE']['format'],ini.getboolean('PDF','pdf_portrait'))
	marges=(float(ini['PAGE']['marginouter'])+float(ini['PAGE']['margininner']),float(ini['PAGE']['margintop'])+float(ini['PAGE']['marginbottom']))
	recouvrement=[float(ini['MAP']['recouvrement_senscourt']),float(ini['MAP']['recouvrement_senslong'])]
	mapscale=1/float(ini['MAP']['mapscale'])
	
	taille_utile_km=((page[0]-marges[0]-recouvrement[coordpt])/mapscale*0.00001,(page[1]-marges[1]-recouvrement[coordgd])/mapscale*0.00001)
	#print(page,marges,recouvrement,taille_utile_km)
	taille_utile_km_gd=taille_utile_km[coordgd] #page-marge-recouvrement. 
	taille_utile_km_pt=taille_utile_km[coordpt] #attention, cette ligne est fausse, si la longueur utile est inversée par rapport à la page.
	page_km=((page[0]-marges[0])/mapscale*0.00001,(page[1]-marges[1])/mapscale*0.00001)
	page_km_gd=max(page_km)
	page_km_pt=min(page_km)
	
	if ini.getboolean('MAP','optimise_recouvrement'):
		len0=len(gpx2cadres(gpxfile,taille_utile_km_gd,taille_utile_km_pt))
		gd=True
		pt=True
		while pt or gd:
			if gd:
				recouvrement[0] += 0.1
				taille_utile_km=((page[0]-marges[0]-recouvrement[coordpt])/mapscale*0.00001,(page[1]-marges[1]-recouvrement[coordgd])/mapscale*0.00001)
				taille_utile_km_gd=taille_utile_km[coordgd]
				taille_utile_km_pt=taille_utile_km[coordpt]
				print('Recouvrement augmenté à : ',round(recouvrement[0],1),round(recouvrement[1],1))
				lenC=len(gpx2cadres(gpxfile,taille_utile_km_gd,taille_utile_km_pt))
				if lenC>len0:
					recouvrement[0] -= 0.1
					taille_utile_km=((page[0]-marges[0]-recouvrement[coordpt])/mapscale*0.00001,(page[1]-marges[1]-recouvrement[coordgd])/mapscale*0.00001)
					taille_utile_km_gd=taille_utile_km[coordgd]
					taille_utile_km_pt=taille_utile_km[coordpt]
					gd=False
					print('Recouvrement sens long maximal atteint : ',round(recouvrement[0],2))
			if pt:
				recouvrement[1] += 0.1
				taille_utile_km=((page[0]-marges[0]-recouvrement[coordpt])/mapscale*0.00001,(page[1]-marges[1]-recouvrement[coordgd])/mapscale*0.00001)
				taille_utile_km_gd=taille_utile_km[coordgd]
				taille_utile_km_pt=taille_utile_km[coordpt]
				print('Recouvrement augmenté à : ',round(recouvrement[0],1),round(recouvrement[1],1))
				lenC=len(gpx2cadres(gpxfile,taille_utile_km_gd,taille_utile_km_pt))
				if lenC>len0:
					recouvrement[1] -= 0.1
					taille_utile_km=((page[0]-marges[0]-recouvrement[coordpt])/mapscale*0.00001,(page[1]-marges[1]-recouvrement[coordgd])/mapscale*0.00001)
					taille_utile_km_gd=taille_utile_km[coordgd]
					taille_utile_km_pt=taille_utile_km[coordpt]
					pt=False
					print('Recouvrement sens court maximal atteint : ',round(recouvrement[1],2))
		print('Recouvrement optimisé, passé de : ',float(ini['MAP']['recouvrement_senslong']),float(ini['MAP']['recouvrement_senscourt']),' à : ',round(recouvrement[0],1),round(recouvrement[1],1))
		
	print('\nGénération définitive des cadres')
	cadres2csvfile(gpx2cadres(gpxfile,taille_utile_km_gd,taille_utile_km_pt),ini['FILES']['cadrescsv'],page_km_gd,page_km_pt,mapscale)

	
def genere_pdf(cadres):
	print()
	print('Génération du fichier Latex pour le PDF')
	latex=open(ini['PATH']['latex']+'/'+'Carnet'+'.tex','w',encoding='utf-8')	
	latex.write('%Code Latex généré automatiquement par le script cree_carnet.py. \n')
	latex.write('%Contact : http://www.openstreetmap.org/user/JBacc1 \n')
#	latex.write("\\documentclass["+ini['PAGE']['format'].lower()+"paper,11pt]{book}\n")
	latex.write("\\documentclass[11pt]{book}\n")
	latex.write('\\pagestyle{empty}\n')
	latex.write('\\usepackage[french]{babel}\n')
	latex.write('\\usepackage[T1]{fontenc}\n')
	latex.write('\\usepackage[utf8]{inputenc}\n')
	latex.write('\\usepackage{lmodern}\n')
	latex.write('\\usepackage{graphicx}\n')
	if not is_paper_custom(ini['PAGE']['format']):
		if ini.getboolean('PDF','pdf_portrait'):
			latex.write('\\usepackage['+ini['PAGE']['format'].lower()+'paper,top='+ini['PAGE']['margintop']+'cm,bottom='+ini['PAGE']['marginbottom']+'cm,inner='+ini['PAGE']['margininner']+'cm,outer='+ini['PAGE']['marginouter']+'cm]{geometry}\n')
		else:
			latex.write('\\usepackage['+ini['PAGE']['format'].lower()+'paper,top='+ini['PAGE']['margintop']+'cm,bottom='+ini['PAGE']['marginbottom']+'cm,inner='+ini['PAGE']['margininner']+'cm,outer='+ini['PAGE']['marginouter']+'cm, landscape]{geometry}\n')
	else:
		loc_page=formatA(ini['PAGE']['format'],ini.getboolean('PDF','pdf_portrait'))
		latex.write('\\usepackage[paperheight='+str(loc_page[1])+'cm,paperwidth='+str(loc_page[0])+'cm,top='+ini['PAGE']['margintop']+'cm,bottom='+ini['PAGE']['marginbottom']+'cm,inner='+ini['PAGE']['margininner']+'cm,outer='+ini['PAGE']['marginouter']+'cm]{geometry}\n')
	latex.write('\setlength{\parindent}{0cm}\n')
	latex.write('\\usepackage{xcolor}\n')
	latex.write('\\usepackage{stackengine}\n')
	latex.write('\\setlength\\unitlength{0mm}\n')
	latex.write('\\usepackage{transparent}\n')
	if args.rotatepage:
		latex.write('\\usepackage{pdflscape}\n')
	if not args.nooddrotation:
		latex.write('\\usepackage{ifoddpage}\n')
	latex.write('\n\n')

	latex.write('\\begin{document}\n')
	if args.rotatepage:
		latex.write('\\newlength{\\hauteurportrait}\n')
		latex.write('\\setlength{\\hauteurportrait}{\\textheight}\n')
	if ini['PAGE']['format']=="A6":
		latex.write('\\sloppy\n')
	
	if os.path.isfile(ini['PDF']['premiere_page']):
		latex.write('\\includegraphics[height=\\textheight]{'+str.replace(ini['PDF']['premiere_page'],'\\','/')+'}\n')
	else:
		latex.write('%Pas de Première de couverture fournie')
	latex.write('\n')
	if os.path.isfile(ini['PDF']['introduction']):
		with open(ini['PDF']['introduction'],'r',encoding='utf-8') as introfile:
			for line in introfile:
				latex.write(line.replace('\ufeff',''))
	else:
		latex.write('%Pas de fichier d\'introduction fourni')	
	latex.write('\n')
	#latex.write('\\pagebreak\n')
	
	for cadre in cadres:
		description=str2latex(cadre[entete_cadre.index("description")])
		if description=='':
			description=str2latex(cadre[0])
			print('Pas de description fournie, utilisé le nom/réf du cadre par défaut : '+description)
		latex.write("{\\shorthandoff{:}\n")
		if is_portrait(cadre[entete_cadre.index("format")-1]) == (ini.getboolean('PDF','pdf_portrait')):  #portrait et portrait, ou paysage et paysage
			#latex.write('\\clipbox*{0cm 0cm {.9999\\textwidth} {.9999\\textheight}}{%\n')
			latex.write('\\raisebox{{\\topskip-\\height}}[0cm][\\textheight-\\topskip-1cm]{%\n')
			latex.write('\\stackinset{l}{0.525cm}{t}{0.525cm}{\\transparent{0.7}{\\colorbox{white}{\\textcolor{black}{'+description+'}}}}%\n')
			latex.write('{\\stackinset{r}{0.125cm}{b}{-0.04cm}{\\transparent{0.7}{\\colorbox{white}{\\textcolor{black}{\\fontsize{5}{6}\\selectfont{\\copyright \\,OSM, JB}}}}}%\n')
			latex.write('{\\includegraphics[height=0.9999\\textheight]{'+str.replace(localpath,'\\','/')+str.replace(ini['PATH']['cartes'],"./","/")+'/'+cadre[0]+'.png}\n')
			latex.write('}}}\n')
		else: # Portrait en paysage ou paysage en portrait
			if not args.rotatepage:
				latex.write('%Oui, le code qui suit est un peu crado, si vous connaissez plus propre, je suis preneur.\n')
				if args.nooddrotation:
					latex.write('\\raisebox{{\\topskip-\\height}}[0cm][\\textheight-\\topskip-1cm]{%\n')
					latex.write('\\stackinset{l}{\\textwidth-\\baselineskip -0.525cm+.02cm}{t}{0.525cm}{\\rotatebox[origin=r]{-90}{\\transparent{0.7}{\\colorbox{white}{'+description+'}}}}{%\n')
					latex.write('\\stackinset{l}{-0.04cm}{t}{\\textheight-\\widthof{\\fontsize{5}{6}\\selectfont{\\copyright \\,OSM, JB}}-0.175cm}{\\rotatebox{-90}{\\transparent{0.7}{\\colorbox{white}{\\fontsize{5}{6}\\selectfont{\\copyright \\,OSM, JB}}}}}{%\n')
					latex.write('\\includegraphics[angle=270,origin=c,width=\\textwidth]{'+str.replace(localpath,'\\','/')+str.replace(ini['PATH']['cartes'],"./","/")+'/'+cadre[0]+'.png}%\n')
					latex.write('}')#pas de \n ici
					latex.write('}}\n')
				else:
					latex.write('\\checkoddpage\n')
					latex.write('\\ifoddpage\n')
					
					latex.write('\\raisebox{{\\topskip-\\height+0.05cm}}[0cm][\\textheight-\\topskip-1cm]{%\n') ###0.05 pour rattraper la sortie du cadre du copyright vers le bas
					#latex.write('\\stackinset{l}{0.525cm}{b}{0.525cm}{\\rotatebox[origin=r]{90}{\\transparent{0.7}{\\colorbox{white}{'+description+'}}}}{%\n')
					latex.write('\\stackinset{l}{0.525cm}{t}{{\\paperheight-0.525cm-0.18cm-\\widthof{'+description+'}}}{\\rotatebox{90}{\\transparent{0.7}{\\colorbox{white}{'+description+'}}}}{%\n')
					latex.write('\\stackinset{r}{-0.04cm}{t}{-0.05cm}{\\rotatebox{90}{\\transparent{0.7}{\\colorbox{white}{\\fontsize{5}{6}\\selectfont{\\copyright \\,OSM, JB}}}}}{%\n')
					latex.write('\\includegraphics[angle=90,origin=c,width=\\textwidth]{'+str.replace(localpath,'\\','/')+str.replace(ini['PATH']['cartes'],"./","/")+'/'+cadre[0]+'.png}%\n')
					latex.write('}')
					latex.write('}}\n')
					
					latex.write('\\else\n')
					
					latex.write('\\raisebox{{\\topskip-\\height}}[0cm][\\textheight-\\topskip-1cm]{%\n')
					latex.write('\\stackinset{l}{\\textwidth-\\baselineskip -0.525cm+.02cm}{t}{0.525cm}{\\rotatebox[origin=r]{-90}{\\transparent{0.7}{\\colorbox{white}{'+description+'}}}}{%\n')
					latex.write('\\stackinset{l}{-0.04cm}{t}{\\textheight-\\widthof{\\fontsize{5}{6}\\selectfont{\\copyright \\,OSM, JB}}-0.175cm}{\\rotatebox{-90}{\\transparent{0.7}{\\colorbox{white}{\\fontsize{5}{6}\\selectfont{\\copyright \\,OSM, JB}}}}}{%\n')
					latex.write('\\includegraphics[angle=270,origin=c,width=\\textwidth]{'+str.replace(localpath,'\\','/')+str.replace(ini['PATH']['cartes'],"./","/")+'/'+cadre[0]+'.png}%\n')
					latex.write('}')
					latex.write('}}\n')
					
					latex.write('\\fi\n')
					
			else: ###Passage en format paysage
				latex.write('\\begin{landscape}\n')
				latex.write('{\\shorthandoff{:}\n')
				#latex.write('\\clipbox*{0cm 0cm {0.9999\\hauteurportrait} {0.9999\\textheight}}{%\n')
				latex.write('\\raisebox{{\\topskip-\\height}}[0cm][\\textheight-\\topskip-1cm]{%\n')
				latex.write('\\stackinset{l}{0.525cm}{t}{0.525cm}{\\transparent{0.7}{\\colorbox{white}{\\textcolor{black}{'+description+'}}}}%\n')
				latex.write('{\\stackinset{r}{0.125cm}{b}{-0.04cm}{\\transparent{0.7}{\\colorbox{white}{\\textcolor{black}{\\fontsize{5}{6}\\selectfont{\\copyright \\,OSM, JB}}}}}%\n')
				latex.write('{\\includegraphics[width=\\hauteurportrait]{'+str.replace(localpath,'\\','/')+str.replace(ini['PATH']['cartes'],"./","/")+'/'+cadre[0]+'.png}\n')
				latex.write('}}}}\n')
				latex.write('\\end{landscape}\n')
				latex.write('\\newpage\n')

		latex.write('}\n')
		latex.write('\\pagebreak\n\n')
	latex.write('\n')
		
	### Fin des cartes. Pages de conclusion.
	latex.write('\\newgeometry{top=0.095\\textheight,bottom=0.095\\textheight,inner=0.19\\textwidth,outer=0.145\\textwidth}\n')
	latex.write('\\vspace*{1cm}\n')
	latex.write('\\vspace {1cm}\n')

	latex.write('\\vspace{ \\stretch{5}}\n')
	latex.write('Cartes :\n')
	latex.write('\\begin{itemize}\n')
	for cadre in cadres:
		latex.write('\\item '+str2latex(cadre[entete_cadre.index("description")])+'\n')
	latex.write('\\end{itemize}\n\n')
	
	latex.write('\\pagebreak[2]\n')
	latex.write('\\vspace*{0.001cm}\n')
	latex.write('\\vspace{\stretch{3}}\n')
	
	latex.write('\\vspace{ \\stretch{1} }\n')
	latex.write('Licences :\n')
	latex.write('\\begin{itemize}\n')
	latex.write("\\item Donn\\'ees :\n")
	latex.write('\\begin{description}\n')
	latex.write('\\item \\copyright \\,les contributeurs d\'OpenStreetMap \n')
	latex.write('\\end{description}\n')
	latex.write("\\item Repr\\'esentation :\n")
	latex.write('\\begin{description}\n')
	latex.write('\\item CC-by-SA JB (OSM : JBacc1)\n')
	latex.write('\\end{description}\n')
	latex.write('\\end{itemize}\n\n')
	
	latex.write('\\pagebreak[2]\n')
	latex.write('\\vspace*{0.001cm}\n')
	latex.write('\\vspace{\\stretch{1}}\n')
	
	latex.write('Des questions, des remarques :\n')
	latex.write('\\begin{itemize}\n')
	latex.write('\\item www.forum.openstreetmap.fr \n')
	latex.write('\\item www.openstreetmap.org/user/JBacc1\n')
	latex.write('\\end{itemize}\n')
	latex.write('\\restoregeometry\n')
	latex.write('\\pagebreak\n\n')
	
	latex.write('\\setlength{\\parindent}{0.095\\textwidth}\n')
	latex.write('\\vspace*{0.05\\textheight}\n')
	if is_assemblage_portrait(ini['FILES']['assemblageosm'],min(formatA(ini['PAGE']['format'],True))-float(ini['PAGE']['margininner'])-float(ini['PAGE']['marginouter']),max(formatA(ini['PAGE']['format'],True))-float(ini['PAGE']['margintop'])-float(ini['PAGE']['marginbottom']))=='portrait':
		latex.write('\\includegraphics[height=0.85\\textheight]{'+str.replace(localpath,'\\','/')+str.replace(ini['PATH']['cartes'],"./","/")+'/'+"assemblage"+'.png'+'}\n')
	else:
		latex.write('\\includegraphics[width=0.9\\textwidth]{'+str.replace(localpath,'\\','/')+str.replace(ini['PATH']['cartes'],"./","/")+'/'+"assemblage"+'.png'+'}\n')
	
	latex.write('\\end{document}\n')
	latex.close()
	print('Génération OK')
	
	popstr='"'+ress['RESSOURCES']['pdflatex']+'" -synctex=1 -output-directory='+ini['PATH']['latex']+' -interaction=nonstopmode '+ini['PATH']['latex']+'/'+'Carnet'+'.tex'
	print('Génération du PDF avec Latex. Ligne de code :')
	print(popstr)	
	pop=Popen(popstr)
	pop.wait()
	print('\nGénération du pdf une seconde fois pour obtenir les transparences et paginations correctes.\n')
	pop=Popen(popstr)
	pop.wait()
	print("Génération OK")
	
	try:
		Popen('"'+ress['RESSOURCES']['pdfreader']+'"'+' '+localpath+(ini['PATH']['latex']).replace('./','/')+'/Carnet.pdf')
		pop.wait()
	except:
		print("L'éditeur de pdf n'est pas spécifié ou n'a pas été trouvé")
	

if __name__ == '__main__':
	parser=argparse.ArgumentParser()
	parser.add_argument("--gpxfile", "-gpx", type=str, help="Génére les cadres de cartes, les cartes et le pdf final, \nou complément de -csv pour indiquer le gpx à surimprimer aux cartes si demandé dans le fichier .ini.\nFichier .GPX attendu")
	parser.add_argument("--csvfile", "-csv", type=str, help="Génère les cartes et le pdf final. Fichier .csv de cadres attendu")
	parser.add_argument("--csvfile2pdf", "-pdf", type=str, help="Génère le pdf final à partir des cartes supposées prégénérées. Fichier .csv de cadres attendu")
	parser.add_argument("--import2csv", "-imp", type=str, help="Importe un fichier de type imp_cadres.csv vers un fichier de cadres standardisé")
	parser.add_argument("--exportcsv", "-exp", type=str, help="Exporte un fichier de type cadres.csv standardisé vers un fichier de cadres importable")
	parser.add_argument("--atlas", "-atl", type=str, help="Mode atlas : pave la zone avec des cadres. Paramètres : --atlas=left,bottom,right,top")
	parser.add_argument("--inifile", "-ini", type=str, help="Fichier .ini à utiliser.\nSi non précisé, CarnetRando.ini sera utilisé par défaut")
	parser.add_argument("--forceportrait", "-fp", help="Force les cartes en format portrait", action="store_true", default=None)
	parser.add_argument("--forcelandscape", "-fl", help="Force les cartes en format paysage", action="store_true", default=None)
	parser.add_argument("--assemblageonly", "-ao", help="Génère uniquement l'assemblage et ouvre son image.\nUtile essentiellement pour tester les paramètres de découpe", action="store_true", default=False)
	parser.add_argument("--nopdf", "-np", help="Ne génère pas de pdf", action="store_true", default=False)
	parser.add_argument("--rotatepage", "-rp", help="Pivote les pages du PDF dont la carte est en format paysage", action="store_true", default=False)
	parser.add_argument("--nooddrotation", "-nor", help="Empêche la rotation de mise du nord à gauche pour les cartes en format paysage sur les pages impaires. Sans effet si --rotatepage est à true", action="store_true", default=False)
	parser.add_argument("--atlascolumn", "-col", help="Ordre de l'atlas : colonnes puis lignes. Défaut=False, lignes puis colonnes", action="store_true", default=False)
	args = parser.parse_args()
	#print(args)

	localpath=os.path.dirname(os.path.realpath(__file__))
	
	time_ini=time.time()
	
	print()
	print("cree_carnet.py 1.0 de JB sous licence FTWPL")
	print("Contact : http://www.openstreetmap.org/user/JBacc1\n")

	ress = configparser.ConfigParser()
	if os.path.isfile(ressfilename):
		print('Chargement du fichier de ressources '+ressfilename)
		ress.read(ressfilename)
	else:
		print('Le fichier de localisation des ressources « '+ressfilename+" » n'a pas été trouvé. Veuillez le retrouver avant de réessayer")
		sys.exit()		
	ini = configparser.ConfigParser()
	try:
		if os.path.isfile(args.inifile):
			inifilename=args.inifile
			print('Utilisation du fichier .ini : '+args.inifile)
		else:
			print('Fichier .ini : '+args.inifile+' introuvable. Utilisation du fichier CarnetRando.ini par défaut')
	except:
		print('Pas de fichier .ini spécifique fourni. Utilisation de CarnetRando.ini par défaut.')
	ini.read(inifilename)
		
	if not os.path.isdir(ini['PATH']['osmfiles']):
		makedirs(ini['PATH']['osmfiles'])
	if not os.path.isdir(ini['PATH']['scripts']):
		makedirs(ini['PATH']['scripts'])
	if not os.path.isdir(ini['PATH']['latex']):
		makedirs(ini['PATH']['latex'])
	if not os.path.isdir(ini['PATH']['cartes']):
		makedirs(ini['PATH']['cartes'])
	
	
	if args.import2csv:
		import_cadres(args.import2csv,ini['FILES']['cadrescsv'])
		if args.assemblageonly:
			script_global_cadres2cartes(ini['FILES']['cadrescsv'])
	elif args.exportcsv:
		export_cadres(args.exportcsv,args.exportcsv[:len(args.exportcsv)-4]+'_export.csv')
	elif args.csvfile2pdf:
##$$ prévoir une option pour générer l'assemblage ici.
		if args.gpxfile:
			args.assemblageonly=True
			script_global_cadres2cartes(args.csvfile2pdf)
		genere_pdf(load_cadres_table(args.csvfile2pdf))
	elif args.atlas:
		script_global_pavage2cadres([float(i) for i in args.atlas.split(",")])
		script_global_cadres2cartes(ini['FILES']['cadrescsv'])
		if not args.nopdf:
			genere_pdf(load_cadres_table(ini['FILES']['cadrescsv']))
	elif args.csvfile:
		script_global_cadres2cartes(args.csvfile)
		if not args.nopdf:
			genere_pdf(load_cadres_table(args.csvfile))
	elif args.gpxfile:
		script_global_gpx2cadres(args.gpxfile)
		script_global_cadres2cartes(ini['FILES']['cadrescsv'])
		if not args.nopdf:
			genere_pdf(load_cadres_table(ini['FILES']['cadrescsv']))
	else:
		print('\nMerci de fournir soit un fichier GPX pour calculer les découpes, soit un fichier csv contenant les découpes. Le fichier '+inifilename+' contient les autres éléments nécessaires.')

	print('Terminé. Exécuté en '+str(round(time.time()-time_ini))+'s')	
	print()

else:
	print("Chargement de cree_carnet.py 1.0 de JB sous licence FTWPL…")
	print("Contact : http://www.openstreetmap.org/user/JBacc1\n")
	