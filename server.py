
from http.server import BaseHTTPRequestHandler, HTTPServer  #Web Server con modulo http 
import re                                                   #Expresiones regulares de caracteres que definen un patrón de búsqueda
import redis                                                #Para almacenar, recuperar información sobre libros y hacer búsquedas
from http.cookies import SimpleCookie                       #Trabajar con cookies HTTP 
import uuid                                                 #Generación de identificadores únicos
from urllib.parse import parse_qsl, urlparse                #Trabajar un urls
from bs4 import BeautifulSoup                               #Analizar html


#Define las rutas y los métodos que se llamarán cuando se acceda a esas rutas
mappings = {
        (r"^/books/(?P<book_id>\d+)$", "get_books"), #patrón de URL que coincide con "/books/", seguido de un número (\d+) que representa el ID del libro. (?P<book_id>...) se utiliza para capturar el ID del libro. "get_books" es el nombre de la función que maneja la solicitud para obtener información sobre el libro
        (r"^/$", "index"), #función que maneja la solicitud para la página de inicio
        (r"^/search", "search") #función que maneja la búsqueda de libros.
        }

#Crea un objeto de conexión a una base de datos
r = redis.StrictRedis(host="localhost", port=6379, db=0)

class WebRequestHandler(BaseHTTPRequestHandler): #maneja las solicitudes HTTP entrantes y genera las respuestas correspondientes
     
    @property
    def url(self):  #maneja las solicitudes HTTP entrantes y genera las respuestas correspondientes
        return urlparse(self.path)
                                    
    @property 
    def query_data(self):   #maneja las solicitudes HTTP entrantes y genera las respuestas correspondientes
        return dict(parse_qsl(self.url.query))
        

    def search(self):
        query_key = self.query_data.get('q') #Obtención del término de búsquedar
        if query_key:
            # Realizar búsqueda en Redis
            matching_books = r.smembers(query_key) #Realización de la búsqueda en Redis:
            
            if matching_books:          #Generación de la respuesta HTML
                self.send_response(200) #Codigo que indica exito si se encuentrar libros coincidentes
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                # Formulario de búsqueda
                response = b""" 
                    <form action="/search" method="GET">
                        <label for="q">Search</label>
                        <input type="text" name="q"/>
                        <input type="submit" value="Buscar Libros"/>
                    </form>
                    <h1>Resultados de la busqueda:</h1>
                    <ul>
                """
                for book_id in matching_books:                      #Iteracion de libros coincidentes
                    book_info = r.get(f"book: {book_id.decode()}") #Se obtiene la info del libro y se convierte el ID del libro a una cadena
                    if book_info:                                   #Verificamos si la info del libro existe
                        soup = BeautifulSoup(book_info, 'html.parser') #Analizamos el HTML y extraemos los datos
                        title = soup.find('h2').text                    #Obtenemos el titulo del libro que esta dentro de h2   
                        response += f"<li><a href='/books/{book_id.decode()}'>{title}</a></li>".encode() #Cadena que te lleva a la URL del libro con el ID especifico
                response += b"</ul>" #Se cierra la lista
                self.wfile.write(response) #El cliente escribe la respuesta
                return #termina la ejecucion de la funcion search

        # Si no se encuentran coincidencias de libros
        self.send_response(404)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        # Mostrar el formulario de búsqueda en la parte superior
        error_message = f"""
        <form action="/search" method="GET">
            <label for="q">Search</label>
            <input type="text" name="q" value="{query_key}"/> <!-- Mostrar el término buscado -->
            <input type="submit" value="Buscar Libros"/>
        </form>
        <h1>No se han encontrado coincidencias para '{query_key}'</h1>
        """.encode()
        self.wfile.write(error_message)

    def cookies(self):  #Obtiene y maneja las cookies por el cliente en la solicitud HTTP
        return SimpleCookie(self.headers.get("Cookie"))

    def get_session(self):          #Obtiene el ID del usuario
        cookies = self.cookies()    #Obtiene todas las cookies presentes
        session_id = None           #Verifica si existe una cookie llamada session_id
        if not cookies:
            session_id = uuid.uuid4() #Sino se encuentra la cookie se genera un nuevo ID de sesion     
        else:                           #Identificador único universal (UUID)
            session_id = cookies["session_id"].value    #Si la cookie "session_id" está presente, se usa su valor como el ID de sesión
        return session_id
            
    def write_session_cookie(self, session_id): #Escribe una cookie de sesión en la respuesta HTTP que se enviará al cliente
        cookies = SimpleCookie()                #Crea un objeto SimpleCookie
        cookies["session_id"] = session_id      #Establece el valor de la cookie "session_id" al ID de sesión proporcionado
        cookies["session_id"]["max-age"] = 10   #Establece el tiempo de vida máximo de la cookie en segundos
        self.send_header("Set-Cookie", cookies.output(header="")) #Agregar la cookie al encabezado de la respuesta HTTP

    def do_GET(self):   #Maneja las solicitudes HTTP GET entrantes
        self.url_mapping_response()

    def url_mapping_response(self):         #Mapea la URL de la solicitud entrante a la función correspondiente
        for pattern, method in mappings:    #Itera sobre el conjunto de mapeos definidos en la variable "mappings"
            match = self.get_params(pattern, self.path) #Intenta encontrar una coincidencia entre el patrón de la URL y la URL de la solicitud actual
            if match is not None:           #Si se encuentra una coincidencia
                md = getattr(self, method)  #Obtiene la función correspondiente al método del mapeo
                md(**match)                 #Llama a la función correspondiente con los parámetros obtenidos de la URL
                return

        self.send_response(404)
        self.end_headers()                              #sino se encuentra ninguna coincidencia
        error = f"<h1> Not found </h1>".encode("utf-8") #se envia una respuesta de error
        self.wfile.write(error)

    def get_params(self, pattern, path):    #Extrae los parámetros de una URL que coinciden con un patrón específico.
        match = re.match(pattern, path)     #Intenta encontrar una coincidencia entre el patrón de la URL y la URL de la solicitud actual
        if match:                           #Si hay una coincidencia
            return match.groupdict()        #Devuelve un diccionario que contiene los parámetros capturados del patrón de la URL

    def get_books(self, book_id):
        session_id = self.get_session() #Se obtiene el identificador de sesión
        book_recommendation = self.get_book_recommendation( str(session_id), book_id) #Se obtiene una recomendación de libro para el usuario actual, basada en su sesión y el libro actual que está siendo consultado.
        
        self.send_response(200) #Se envía una respuesta HTTP con el código de estado 200 (OK) para indicar que la solicitud fue exitosa.
        self.send_header("Content-Type", "text/html") #Se envía una cabecera HTTP para especificar que el contenido de la respuesta es de tipo HTML.
        self.write_session_cookie(session_id) #Se escribe una cookie de sesión en la respuesta para realizar un seguimiento de la sesión del usuario.
        self.end_headers() #Se finaliza la cabecera HTTP.
        
        book_info = r.get(f"book: {book_id}") or "<h1> No existe el libro </h1>".encode("utf-8") #Si no se encuentra el libro, se establece un mensaje predeterminado de "No existe el libro".
        self.wfile.write(book_info)   #Se escribe la información del libro en el flujo de escritura de la respuesta HTTP para que el cliente la reciba.
        
        #Se crea una cadena de respuesta HTML que incluye información sobre la sesión del usuario 
        #y cualquier recomendación de libro.
        response = f"""
        <p> SESSION: {session_id} </p> 
        <p> Recomendación: </p>
        <ul>
        """
        
        if isinstance(book_recommendation, list):       #Se verifica si book_recommendation es una lista (más de un libro recomendado).
            for recommendation in book_recommendation:  #Se itera sobre cada recomendación de libro.
                book_info = r.get(f"book: {recommendation}") #Se extrae el título del libro.
                soup = BeautifulSoup(book_info, 'html.parser') #Analiza el contenido del libro y se asigna a la variable soup
                title = soup.find('h2').text                    #Se obtiene el titulo del libro
                response += f"<li><a href='/books/{recommendation}'> Libro: {title}</a></li>" #Crea un elemento de lista HTML (<li>) con un enlace (<a>) que apunta a la URL del libro 
        else:                                                       #Si book_recommendation no es una lista
            response += f"<li><a href='/'>{book_recommendation} Menú</a></li>" #Enlace que apunta a la raíz del sitio
        
        response += "</ul>" #Etiqueta de cierre de la lista
        self.wfile.write(response.encode("utf-8")) #Envía la respuesta completa al cliente que realizó la solicitud.       
            
    def get_book_recommendation(self, session_id, book_id):
        r.rpush(session_id, book_id)        #Agrega el ID del libro actual a la lista de libros visitados 
        books = r.lrange(session_id, 0, 7)  #Obtiene los últimos libros visitados para la sesión actual del usuario desde Redis y los almacena en la variable books
        print(session_id, books)            #Imprime el ID de la sesión del usuario y la lista de libros visitados en la consola

        all_books = [ i+1 for i in range(7) ]   #Crea una lista de todos los libros disponibles
        new = [b for b in all_books if b not in
               [int(vb.decode()) for vb in books]] #Crea una lista de libros que el usuario aún no ha visitado

        if len(new) != 0:       #Comprueba si hay libros no visitados en la lista new
            if len(new) < 1:    #Comprueba si hay menos de un libro no visitado en la lista new
                return new[0]   #Devuelve el primer libro no visitado como recomendación
            return new[:1]      #Devuelve los primeros libros no visitados como recomendación
        else:
            return "No mas libros disponibles, increible!"

    def index(self):
        self.send_response(200)     #Respuesta HTTP con 200 (OK) para indicar que la solicitud fue exitosa.
        self.send_header("Content-Type", "text/html")   #Especificar que el contenido de la respuesta es de tipo HTML.
        self.end_headers()  #Se finaliza la cabecera HTTP.
        
        # Formulario de búsqueda
        search_form = """
        <form action="/search" method="GET">
                <label for="q">Search</label>
                <input type="text" name="q"/>
                <input type="submit" value="Buscar Libros"/>
            </form>
        """
    
        # Agrega el formulario de búsqueda al HTML de la página de inicio
        with open('html/index.html') as f: #El archivo se abre en el directorio html y se asigna al identificador f.
            response = f.read() #Se lee el contenido del archivo HTML
            response = response.replace("<h1> Books </h1>", "<h1> Books </h1>" + search_form) #Busca la etiqueta <h1> Books </h1> en el contenido HTML
        self.wfile.write(response.encode("utf-8")) #El contenido HTML modificado se escribe en el flujo de escritura de la respuesta HTTP
        
        

if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()
