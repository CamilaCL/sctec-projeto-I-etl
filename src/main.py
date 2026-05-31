from pathlib import Path

from functions import (
    clean_products,
    format_date_values,
    read_csv,
    summarize_order_cancellations,
    write_csv
)


data_dir = Path(__file__).resolve().parent.parent / 'data'
products_file = data_dir / 'olist_products_dataset.csv'
output_products_file = data_dir / 'olist_products_dataset_cleaned.csv'
orders_file = data_dir / 'olist_orders_dataset.csv'
output_orders_file = data_dir / 'olist_orders_dataset_cleaned.csv'

PRODUCT_CLEANING_CONFIG = {
    'category_column': 'product_category_name',
    'category_empty_value': 'sem_categoria',
    'count_columns': ['product_name_length', 'product_description_length', 'product_photos_qty'],
    'dimension_columns': ['product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm'],
}

def main() -> None:
    print('\n' + '='*60)
    print('      PIPELINE DE SANITIZAÇÃO DE DADOS OLIST - INICIADO      ')
    print('='*60)

    # --- BLOCO DE PRODUTOS ---
    products, product_rows, product_nulls, product_deleted = read_csv(str(products_file), 'product_id')
    cleaned_products, product_totals, product_stats = clean_products(
        products,
        category_column=PRODUCT_CLEANING_CONFIG['category_column'],
        category_empty_value=PRODUCT_CLEANING_CONFIG['category_empty_value'],
        count_columns=PRODUCT_CLEANING_CONFIG['count_columns'],
        dimension_columns=PRODUCT_CLEANING_CONFIG['dimension_columns'],
    )
    
    # Gravando produtos limpos
    write_csv(cleaned_products, output_products_file)

    print('\n┌──────────────────────────────────────────────────────────┐')
    print('│                RELATÓRIO: METADADOS PRODUTOS             │')
    print('├──────────────────────────────────────────────────────────┤')
    print(f'│ {'Registros totais lidos:':<40} {product_rows:>15} │')
    print('│ Total de nulos por coluna:                               │')
    for col, tot in product_nulls.items():
        print(f'│   • {col:<36} {tot:>15} │')
    print(f'│ {'Registros descartados (sem dimensões):':<40} {product_stats['rows_discarded']:>15} │')
    print('│ Resumo da limpeza/tratamento:                            │')
    for col, tot in product_stats.items():
        print(f'│   • {col:<36} {tot:>15} │')
    print(f'│ {'Registros válidos pós-limpeza:':<40} {len(cleaned_products):>15} │')
    print('├──────────────────────────────────────────────────────────┤')
    print('│ VALORES NULOS CORRIGIDOS POR COLUNA:                     │')
    for col, tot in product_totals.items():
        print(f'│   • {col:<36} {tot:>15} │')
    print('└──────────────────────────────────────────────────────────┘')

    # --- BLOCO DE PEDIDOS ---
    orders, order_rows, order_nulls, order_deleted = read_csv(str(orders_file), 'order_id')
    missing_delivery_summary = summarize_order_cancellations(orders)
    formatted_dates = format_date_values(orders, 'order_approved_at')
    
    # Gravando pedidos limpos
    write_csv(orders, output_orders_file)

    print('\n┌──────────────────────────────────────────────────────────┐')
    print('│                 RELATÓRIO: METADADOS PEDIDOS             │')
    print('├──────────────────────────────────────────────────────────┤')
    print(f'│ {'Registros totais lidos:':<40} {order_rows:>15} │')
    print(f'│ {'Registros descartados (linhas vazias):':<40} {len(order_deleted):>15} │')
    print(f'│ {'Datas de aprovação formatadas (PT-BR):':<40} {formatted_dates:>15} │')
    print(f'│ {'Pedidos com data de entrega ausente:':<40} {missing_delivery_summary['missing_delivery_date']:>15} │')
    print('├──────────────────────────────────────────────────────────┤')
    print('│ AUDITORIA DE STATUS (DATA DE ENTREGA AUSENTE):           │')
    
    status_ausentes = missing_delivery_summary['missing_delivery_status_counts']
    for status, qtd in sorted(status_ausentes.items(), key=lambda x: x[1], reverse=True):
        print(f'│   • {status:<36} {qtd:>15} │')
        
    print('└──────────────────────────────────────────────────────────┘')

    print('\n' + '='*60)
    print('         PIPELINE CONCLUÍDO COM SUCESSO (ETL LOAD OK)        ')
    print('='*60 + '\n')

if __name__ == '__main__':
    main()
