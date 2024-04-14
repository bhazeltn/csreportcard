import re
import pandas as pd

def transform_ribbon_names(df, index, pattern, replacement):
    """Transforms ribbon names based on a regex pattern and replacement.

    Args:
        df (pandas.DataFrame): DataFrame with ribbon names.
        index (int): Index of the ribbon name in a tuple if columns are a MultiIndex.
        pattern (str): Regex pattern to match in the ribbon names.
        replacement (str): Replacement string with regex groups.

    Returns:
        pandas.DataFrame: DataFrame with transformed ribbon names.
    """
    if isinstance(df.columns, pd.MultiIndex):
        transformed_columns = []
        for col in df.columns:
            if isinstance(col[index], str):
                new_ribbon = re.sub(pattern, replacement, col[index])
                new_col = col[:index] + (new_ribbon,) + col[index+1:]
            else:
                new_col = col
            transformed_columns.append(new_col)
        df.columns = pd.MultiIndex.from_tuples(transformed_columns)
    else:
        df.columns = [re.sub(pattern, replacement, col) if isinstance(col, str) else col for col in df.columns]
    return df
def apply_transformed_ribbons(df, column_index, transformed_ribbons):
    """Applies transformed ribbon names to the DataFrame."""
    df.iloc[column_index] = transformed_ribbons
    df.columns = pd.MultiIndex.from_arrays(df.iloc[:column_index + 1])
    df.drop(df.index[:column_index + 1], inplace=True)
    return df
