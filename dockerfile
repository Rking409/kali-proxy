# 1. Utiliser une version plus récente et spécifique (Bookworm est plus récent que Bullseye)
FROM python:3.12-alpine

# 2. Mettre à jour les paquets système pour corriger les vulnérabilités OS
RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

# 3. Créer un utilisateur non-root pour ne pas exécuter le proxy avec les droits admin
RUN useradd -m proxyuser
WORKDIR /home/proxyuser

# 4. Copier le fichier et changer le propriétaire
COPY --chown=proxyuser:proxyuser proxy.py .

# 5. Passer à l'utilisateur non-privilégié
USER proxyuser

# Le port 8080 est > 1024, donc autorisé pour un utilisateur non-root
EXPOSE 8080

CMD ["python", "proxy.py"]
