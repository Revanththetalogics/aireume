# O*NET Data Cache

This directory contains cached O*NET occupational data used for occupation-aware skill validation.

## Attribution

This application includes information from the O*NET 30.2 Database by the U.S. Department of Labor, 
Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license.
https://www.onetcenter.org/

## Sync Instructions

To download/update O*NET data:

```bash
python -m app.backend.services.onet.onet_sync
```

The sync script downloads the latest O*NET database and populates the local SQLite cache.

## Update Frequency

O*NET data is updated quarterly. Run the sync script after each O*NET release.
