import os

# gunicorn.conf.py
# Aumenta el timeout para dar tiempo a que los workers de Render inicien.

# El número de workers. Render recomienda 1 para la mayoría de los casos.
workers = int(os.environ.get('GUNICORN_PROCESSES', '1'))

# El número de hilos por worker.
threads = int(os.environ.get('GUNICORN_THREADS', '1'))

# Timeout en segundos. El valor por defecto es 30. Lo aumentamos a 120.
timeout = 120
