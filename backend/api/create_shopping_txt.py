def create_shopping_list(ingredients):
    lines = []

    for ingredient in ingredients:
        name = ingredient['ingredient__name']
        amount = ingredient['total_amount']
        unit = ingredient['ingredient__measurement_unit']
        lines.append(f'{name} = {amount} {unit}')

    return '\n'.join(lines)
