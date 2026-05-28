# Chef en Proceso

Proyecto web en Flask para registrar usuarios, iniciar sesión y guardar recetas.

## Integrantes

- Rosal Castillo Ricardo
- López Lozano Astrid Vanessa

## Fotos

![Foto de Ricardo](static/img/ricardo.jpeg)
![Foto de Astrid](static/img/FOTO.png)

## Configuración

1. Instala las dependencias:

   ```powershell
   uv sync --link-mode=copy
   ```

2. Configura las variables en `.env`:

   ```env
   SECRET_KEY=dev-secret-key
   MONGODB_URI=mongodb://localhost:27017/
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=
   MAIL_PASSWORD=
   ```

3. Ejecuta la app:

   ```powershell
   uv run flask --app app run --debug
   ```
