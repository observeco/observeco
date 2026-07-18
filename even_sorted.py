def even_sorted_desc(numbers: list[int]) -> list[int]:
    return sorted((n for n in numbers if n % 2 == 0), reverse=True)
