import csv
import io
import re
from urllib.parse import urlsplit


def normalize(value):
    value = value.strip()
    if '://' in value or '.' in value and ' ' not in value:
        parsed = urlsplit(value if '://' in value else 'https://' + value)
        if parsed.username or parsed.password or not parsed.hostname or '.' not in parsed.hostname:
            raise ValueError('Enter a valid public company domain.')
        return parsed.hostname.lower().removeprefix('www.')
    if not value or len(value) > 150 or not re.fullmatch(r"[\w &.,'()+/-]+", value):
        raise ValueError('Enter a company name or domain (maximum 150 characters).')
    return value


def ingest(text='', csv_bytes=None):
    values = []
    if csv_bytes is not None:
        try:
            reader = csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig')), strict=True)
            field = next((x for x in reader.fieldnames or [] if x.lower().strip() in {'company','name','domain'}), None)
            if not field:
                raise ValueError('CSV needs a company, name, or domain column.')
            for row in reader:
                if None in row or row.get(field) is None:
                    raise ValueError('CSV row does not match its header.')
                values.append(row[field])
        except (UnicodeError, csv.Error) as exc:
            raise ValueError('Invalid UTF-8 CSV.') from exc
    values.extend(re.split(r'[\n;]+', text))
    result = list(dict((normalize(v).casefold(), normalize(v)) for v in values if v.strip()).values())
    if not result:
        raise ValueError('Enter at least one company.')
    if len(result) > 5:
        raise ValueError('Maximum five unique companies per investigation.')
    return result
