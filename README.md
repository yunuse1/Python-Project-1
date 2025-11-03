# University Price Check System

This application helps users check university prices in Turkey with various filtering options including scholarships and preference discounts.

## Features

- Search universities by name or view all universities
- Search departments by name or view all departments
- View prices with or without half scholarship
- Apply preference discounts for eligible universities
- Export results to CSV file

## Prerequisites

* Python 3.8 or higher
* pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Python-Project-1
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate 
 # On Windows use:
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the program:
```bash
python main.py
```

Follow the prompts to:
1. Select a university or view all universities
2. Choose between full price or half scholarship price
3. Select a department or view all departments
4. Choose whether to apply preference discounts

The results will be saved to `university_department_prices.csv` in the current directory.

## Output Format

The program generates a CSV file with the following columns:
- University name
- Faculty name
- Department name
- Price (with applied discounts if selected)
- Scholarship information

## Notes

- Preference discounts (20%) are available for selected universities
- Half scholarship option reduces the tuition fee by 50%
- All prices are in Turkish Lira (TL)

## Running Tests

To run the tests, use the following command:

```bash
python -m pytest
```
or

```bash
py -m pytest
```

