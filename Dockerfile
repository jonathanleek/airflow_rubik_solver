FROM astrocrpublic.azurecr.io/runtime:3.2-5

ENV AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=False
