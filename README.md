# Easy-DB-viewer

## Overview

Easy DB viewer is a desktop application developed using Python and PyQt5. It provides a user-friendly interface for searching and displaying data from a MySQL database. Users can search based on various criteria and view detailed information from database tables. The interface is designed to be intuitive, making it easy to filter, search, and view results efficiently. (Developed as part of efficiency improvement in the department)

## Features

- **Multi-Criteria Search**: Search using different columns.
- **Detailed Information Display**: View detailed records in the main results area, with additional details available in InfoBoxes.
- **Dynamic Data Filtering**: Filter results dynamically using input fields for each column.
- **Database Interaction**: Connects to a MySQL database, executing queries to fetch and display data in a user-friendly format.
- **Modular Design**: Easy to extend and modify for additional features or data sources.

## Getting Started

### Prerequisites

Before running the application, ensure you have the following software installed:

- **Python 3.7+**: The application is developed using Python, and it's recommended that the latest version be installed.
- **PyQt5**: A set of Python bindings for Qt libraries, providing a robust framework for GUI applications.
- **pymysql**: A Python library used to connect to the MySQL database.

### Installation

1. **Clone the Repository**

   Clone the repository to your local machine using the following command:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install Dependencies**

   Install the necessary Python packages:
   ```
   pip install PyQt5
   pip install pymysql
   ```

3. **Configure Database Connection**

   Configure your database connection by editing the `config.ini` file:
   ```ini
   [database]
   host = your-database-host
   user = your-database-user
   password = your-database-password
   database = your-database-name
   port = your-database-port
   ```

### Running the Application

Run the application using the following command:
```
python main.py
```

## Usage

1. **Search Functionality**

   - **Search by ID, CustomerID, or Description**: Use the top search bar to search by these criteria.
   - **Filter Results**: Use the provided fields to filter results.

2. **View Details**

   - **Main Results Area**: Displays the main search results.
   - **InfoBoxes**: Provide additional detailed information based on the selected record in the main results area.

3. **Dynamic Interaction**

   - Select a record from the main results area to view more details in the InfoBoxes.
   - Use the comboboxes to select different tables and click 'Search' to display related data.

## Contribution

Contributions are welcome! Please fork the repository and submit a pull request with your changes. For major changes, please open an issue to discuss what you would like to change.
```
Feel free to replace `<repository-url>` and `<repository-directory>` with the appropriate values for your repository.
