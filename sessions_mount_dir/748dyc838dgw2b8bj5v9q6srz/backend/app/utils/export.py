import csv
import io
import zipfile
from typing import Any, Dict, List, Optional, Union
from fastapi import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.config import settings
import redis
import json

redis_client = redis.Redis.from_url(settings.REDIS_URL)

class DataExporter:
    def __init__(self, db: Session):
        self.db = db
        self.chunk_size = 1000

    def export_to_csv(
        self,
        query: str,
        filename: str,
        headers: Optional[List[str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Response:
        """
        Export query results to CSV format with streaming support for large datasets
        """
        def generate():
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers if provided
            if headers:
                writer.writerow(headers)
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)
            
            # Stream data in chunks
            offset = 0
            while True:
                chunk_query = f"{query} LIMIT {self.chunk_size} OFFSET {offset}"
                result = self.db.execute(text(chunk_query), params or {})
                rows = result.fetchall()
                
                if not rows:
                    break
                
                for row in rows:
                    writer.writerow(row)
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)
                
                offset += self.chunk_size
                
                # Cache progress for large exports
                if offset % (self.chunk_size * 10) == 0:
                    progress_key = f"export_progress:{filename}"
                    redis_client.setex(progress_key, 3600, json.dumps({"offset": offset}))
        
        response = Response(
            io.BytesIO().join((line.encode('utf-8') for line in generate())),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        return response

    def export_to_excel(
        self,
        data: List[Dict[str, Any]],
        filename: str,
        sheet_name: str = "Sheet1"
    ) -> Response:
        """
        Export data to Excel format (for smaller datasets)
        """
        import pandas as pd
        
        df = pd.DataFrame(data)
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        return Response(
            output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    def export_multiple_sheets(
        self,
        data_dict: Dict[str, List[Dict[str, Any]]],
        filename: str
    ) -> Response:
        """
        Export multiple dataframes to different sheets in Excel
        """
        import pandas as pd
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, data in data_dict.items():
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        return Response(
            output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    def export_to_json(
        self,
        query: str,
        filename: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Response:
        """
        Export query results to JSON format with streaming support
        """
        def generate():
            yield '['
            first = True
            offset = 0
            
            while True:
                chunk_query = f"{query} LIMIT {self.chunk_size} OFFSET {offset}"
                result = self.db.execute(text(chunk_query), params or {})
                rows = result.fetchall()
                
                if not rows:
                    break
                
                for row in rows:
                    if not first:
                        yield ','
                    yield json.dumps(dict(row._mapping))
                    first = False
                
                offset += self.chunk_size
            
            yield ']'
        
        response = Response(
            io.BytesIO().join((line.encode('utf-8') for line in generate())),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        return response

    def create_export_archive(
        self,
        files: Dict[str, Union[str, bytes]],
        archive_name: str
    ) -> Response:
        """
        Create a ZIP archive containing multiple export files
        """
        output = io.BytesIO()
        
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, content in files.items():
                if isinstance(content, str):
                    zipf.writestr(filename, content.encode('utf-8'))
                else:
                    zipf.writestr(filename, content)
        
        output.seek(0)
        return Response(
            output.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={archive_name}"}
        )

    def get_export_progress(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get the progress of a large export operation
        """
        progress_key = f"export_progress:{filename}"
        progress_data = redis_client.get(progress_key)
        
        if progress_data:
            return json.loads(progress_data)
        return None

    def cleanup_export_cache(self, filename: str) -> None:
        """
        Clean up progress cache for an export
        """
        progress_key = f"export_progress:{filename}"
        redis_client.delete(progress_key)
