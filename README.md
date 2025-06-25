# Arquitectura AWS con Terraform + GitHub Actions

Este proyecto despliega una arquitectura completa en AWS:
- Producer sube archivos a S3
- Lambda limpia los archivos y los transforma en JSON
- EC2 sirve los archivos por HTTP vía Flask

## Pasos para usar

1. Configura los secretos `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` en tu repositorio de GitHub
2. Ejecuta:
```bash
git init
git add .
git commit -m "infraestructura completa"
git push origin main
```
3. Terraform y GitHub Actions desplegarán todo automáticamente