import csv
from io import BytesIO
from django.http import HttpResponse
from openpyxl import Workbook


def export_response(data_rows, headers, filename_prefix, export_format="json"):
    """
    data_rows: list of dicts or lists
    headers: list of string column titles
    export_format: 'json' | 'csv' | 'excel'
    """
    if export_format == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename_prefix}.csv"'
        writer = csv.writer(response)
        writer.writerow(headers)
        for row in data_rows:
            if isinstance(row, dict):
                writer.writerow([row.get(h, "") for h in headers])
            else:
                writer.writerow(row)
        return response

    elif export_format == "excel":
        wb = Workbook()
        ws = wb.active
        ws.title = "Report"

        # Write header
        ws.append(headers)

        # Write data
        for row in data_rows:
            if isinstance(row, dict):
                ws.append([str(row.get(h, "")) for h in headers])
            else:
                ws.append([str(cell) for cell in row])

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename_prefix}.xlsx"'
        return response

    # Default JSON return handled directly in views
    return None
