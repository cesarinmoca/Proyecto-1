import os       #Sistema Operativo
import redis    #BD de Redis
import re       #Epresiones Regulares
from bs4 import BeautifulSoup #Analizar HTML

#Conexion con la BD de Redis
r = redis.StrictRedis()

def load_dir(path):         #Funcion para cargar archivos HTML en la BD         
    files = os.listdir(path)    #Obtiene una lista de archivos en el directorio especificado.           
    for f in files:             #Itera sobre cada archivo en el directorio.  
        match = re.match(r"book(\d+).html$", f) #Comprueba si el nombre del archivo coincide con el patrón "book<numero>.html".      
        if match is not None: #Si hay una coincidencia:                
            with open(path + f) as file:    #Abre el archivo en modo lectura.                         
                html = file.read()          #Lee el contenido del archivo HTML.                     
                book_id = match.group(1)    #Obtiene el ID del libro a partir del nombre del archivo
                create_index(book_id, html) #Llama a la función para crear el índice de términos.
                r.set(f"book: {book_id}", html) #Almacena el contenido HTML del libro en Redis.
                print(f"file {file} loaded into redis...")  #Imprime un mensaje indicando que el archivo se cargó en Redis.

#Función para crear un índice de términos a partir del contenido HTML de un libro.
def create_index(book_id, html):
    soup = BeautifulSoup(html, 'html.parser') #Analiza el HTML
    ts = soup.get_text().split(' ') #Obtiene el texto sin formato del HTML y Divide el texto en términos individuales.
    for term in ts:             #Itera sobre cada término.
        r.sadd(term, book_id)   #Agrega el término al conjunto en Redis con el ID del libro.

load_dir("html/books/") #Llama a la función para cargar los archivos HTML del directorio especificado.