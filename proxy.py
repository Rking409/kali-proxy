import socket
import threading
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

class PyProxy:
    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen(100)
        logging.info(f"Proxy actif sur {self.host}:{self.port}")

        while True:
            client_sock, addr = self.server.accept()
            logging.info(f"Connexion entrante de {addr[0]}")
            thread = threading.Thread(target=self.proxy_thread, args=(client_sock,))
            thread.start()

    def proxy_thread(self, client_sock):
        try:
            # Recevoir les données brutes (octets)
            request = client_sock.recv(4096)
            if not request:
                return

            # On ne décode QUE la première ligne pour l'analyse
            # On utilise 'latin-1' qui ne plante jamais, contrairement à 'utf-8'
            try:
                first_line = request.split(b'\n')[0].decode('latin-1').strip()
                logging.info(f"Requête : {first_line}")
                
                parts = first_line.split(' ')
                if len(parts) < 3:
                    return
                
                method, url, _ = parts
            except Exception as e:
                logging.error(f"Erreur décodage ligne : {e}")
                return

            if method == "CONNECT":
                self.handle_https(client_sock, url)
            else:
                self.handle_http(client_sock, request, url)

        except Exception as e:
            logging.error(f"Erreur générale : {e}")
        finally:
            client_sock.close()

    def handle_http(self, client_sock, request, url):
        try:
            # 1. Extraire l'hôte de l'URL ou des Headers
            target_host = ""
            target_port = 80

            # Si l'URL est complète (http://...)
            if "://" in url:
                url = url.split("://")[1]
            
            parts = url.split("/")
            host_parts = parts[0].split(":")
            target_host = host_parts[0]
            if len(host_parts) > 1:
                target_port = int(host_parts[1])

            # 2. Si l'hôte est vide (requête relative), on cherche dans le header "Host"
            if not target_host or target_host == "/":
                lines = request.decode('latin-1').split('\r\n')
                for line in lines:
                    if line.startswith("Host:"):
                        host_val = line.split(" ")[1]
                        if ":" in host_val:
                            target_host, target_port = host_val.split(":")
                            target_port = int(target_port)
                        else:
                            target_host = host_val
                        break

            if not target_host:
                logging.error("Impossible de trouver l'hôte cible")
                return

            logging.info(f"Relais vers : {target_host}:{target_port}")

            # 3. Connexion au serveur cible
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as target_sock:
                target_sock.settimeout(5.0) # Éviter de bloquer indéfiniment
                target_sock.connect((target_host, target_port))
                target_sock.sendall(request)
                
                while True:
                    data = target_sock.recv(4096)
                    if not data: break
                    client_sock.sendall(data)

        except Exception as e:
            logging.error(f"Erreur HTTP vers {target_host} : {e}")

    def handle_https(self, client_sock, url):
        target_host, target_port = url.split(":")
        target_port = int(target_port)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as target_sock:
            try:
                target_sock.connect((target_host, target_port))
                # Répondre au client que la connexion est établie (Tunneling)
                client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                
                # Relais bidirectionnel entre le client et le serveur
                self.forward_data(client_sock, target_sock)
            except Exception as e:
                logging.error(f"Erreur HTTPS : {e}")

    def forward_data(self, sock1, sock2):
        # Fonction simple pour transférer les flux
        sock1.setblocking(False)
        sock2.setblocking(False)
        while True:
            try:
                data = sock1.recv(4096)
                if not data: break
                sock2.sendall(data)
            except: pass
            try:
                data = sock2.recv(4096)
                if not data: break
                sock1.sendall(data)
            except: pass

if __name__ == "__main__":
    proxy = PyProxy()
    proxy.start()
