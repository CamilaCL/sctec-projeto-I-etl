import csv
import re
from datetime import datetime
from pathlib import Path
import unicodedata


def is_empty_value(value):
    '''Return True when a CSV field is empty or contains only whitespace.'''
    return value is None or str(value).strip() == ''


def read_csv(file_path, id_column, encoding='utf-8'):
    '''Read a CSV file and return the rows plus null statistics.
    The function reads the file using csv.DictReader and counts null or empty
    values per column. Rows in which all fields except the identifier are
    empty are ignored as they do not contribute useful information.
    '''
    data = []
    total_rows = 0
    null_counts = {}
    deleted_ids = []

    path = Path(file_path)

    try:
        with path.open(mode='r', encoding=encoding, newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                total_rows += 1
                all_other_values_empty = True
                for key, value in row.items():
                    if is_empty_value(value):
                        null_counts[key] = null_counts.get(key, 0) + 1
                    if key != id_column and not is_empty_value(value):
                        all_other_values_empty = False

                if all_other_values_empty:
                    deleted_ids.append(row.get(id_column, ''))
                    continue

                data.append(row)
    except Exception as e:
        print(f'[ERRO] Não foi possível ler o arquivo: {file_path}')
        return [], 0, {}, []

    return data, total_rows, null_counts, deleted_ids


def normalize_text(
    value,
    lower=True,
    strip=True,
    collapse_spaces=True,
    pattern=r'[^a-z0-9_]',
    ):
    '''Normalize text values for consistent comparison and grouping.'''
    if is_empty_value(value):
        return ''

    normalized = str(value)
    if strip:
        normalized = normalized.strip()
    if lower:
        normalized = normalized.lower()
    if collapse_spaces:
        normalized = re.sub(r'\s+', ' ', normalized)
    if pattern:
        normalized = unicodedata.normalize('NFKD', normalized).encode('ASCII', 'ignore').decode('ASCII')
        normalized = re.sub(pattern, '', normalized)
    return normalized


def should_discard_row(row, required_columns):
    '''Determine if a row should be discarded because required values are all empty.'''
    return all(is_empty_value(row.get(column)) for column in required_columns)


def clean_products(
    products,
    category_column='product_category_name',
    category_empty_value='sem_categoria',
    count_columns=None,
    dimension_columns=None,
    ):
    '''Performs data cleansing, null imputation, and filtering of the product dataset.
    It applies cutoff rules based on physical dimensions, standardizes textual categories via normalization, and fills in missing numeric values ​​coherently.
    '''
    if count_columns is None:
        count_columns = ['product_name_length', 'product_description_length', 'product_photos_qty']
    if dimension_columns is None:
        dimension_columns = ['product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm']

    totals = {
        category_column: 0,
        count_columns[0]: 0,
        count_columns[1]: 0,
        count_columns[2]: 0,
    }
    stats = {
        'rows_processed': 0,
        'rows_discarded': 0
    }

    cleaned_products = []
    for product in products:
        stats['rows_processed'] += 1

        if should_discard_row(product, dimension_columns):
            stats['rows_discarded'] += 1
            continue

        if is_empty_value(product.get(category_column)):
            product[category_column] = category_empty_value
            totals[category_column] += 1

        product[category_column] = normalize_text(product[category_column])

        for column in count_columns:
            if is_empty_value(product.get(column)):
                product[column] = 0
                totals[column] += 1

        cleaned_products.append(product)

    return cleaned_products, totals, stats


def format_date_values(
    rows,
    column_name,
    source_format='%Y-%m-%d %H:%M:%S',
    target_format='%d/%m/%Y',
    ):
    '''Convert date strings in a column from one format to another.'''
    formatted_count = 0
    for row in rows:
        raw_value = row.get(column_name)
        if is_empty_value(raw_value):
            continue
        try:
            parsed = datetime.strptime(raw_value.strip(), source_format)
            row[column_name] = parsed.strftime(target_format)
            formatted_count += 1
        except ValueError:
            continue
    return formatted_count


def summarize_order_cancellations(
    orders,
    delivery_column='order_delivered_customer_date',
    status_column='order_status',
    canceled_label='canceled',
    ):
    '''Summarize orders with missing delivery dates and identify canceled orders.'''
    summary = {
        'total_orders': len(orders),
        'missing_delivery_date': 0,
        'missing_delivery_and_canceled': 0,
        'missing_delivery_status_counts': {}
    }
    status_counts = {}
    for order in orders:
        if is_empty_value(order.get(delivery_column)):
            summary['missing_delivery_date'] += 1
            status_norm = normalize_text(order.get(status_column))
            if status_norm:
                status_counts[status_norm] = status_counts.get(status_norm, 0) + 1
            if status_norm == canceled_label:
                summary['missing_delivery_and_canceled'] += 1

    summary['missing_delivery_status_counts'] = status_counts
    return summary


def write_csv(data, file_path, encoding='utf-8'):
    '''Saves a list of dictionaries to a native CSV file.
    If the list is empty, the function does not create the file to avoid empty header errors.
    '''
    if not data:
        print(f'Aviso: Nenhum dado fornecido para salvar em {file_path}.')
        return False

    path = Path(file_path)
    
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(data[0].keys())

    try:
        with path.open(mode='w', encoding=encoding, newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(data)
            
        return True
    except (PermissionError, IOError) as e:
        print(f'Erro ao salvar o arquivo {file_path}: {e}')
        return False