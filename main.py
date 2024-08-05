import sys
import pymysql
import configparser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QTextEdit, QComboBox, QGridLayout, QFrame, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QInputDialog)
from PyQt5.QtCore import pyqtSlot, Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Search Results Interface")
        self.setGeometry(100, 100, 1024, 720)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # Top control area
        self.search_textbox = QLineEdit(self)
        self.search_textbox.setPlaceholderText("Search by Id, CustomerId, or Description")
        self.search_textbox.returnPressed.connect(self.search_textbox_keydown)
        main_layout.addWidget(self.search_textbox)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side - search results and subresults
        left_layout = QVBoxLayout()

        # Search boxes for each column
        search_boxes_layout = QHBoxLayout()
        self.customer_id_search = QLineEdit(self)
        self.customer_id_search.setPlaceholderText("Search CustomerID")
        self.customer_id_search.textChanged.connect(self.filter_results)
        search_boxes_layout.addWidget(self.customer_id_search)

        self.is_active_search = QLineEdit(self)
        self.is_active_search.setPlaceholderText("Search IsActive")
        self.is_active_search.textChanged.connect(self.filter_results)
        search_boxes_layout.addWidget(self.is_active_search)

        self.package_id_search = QLineEdit(self)
        self.package_id_search.setPlaceholderText("Search PackageID")
        self.package_id_search.textChanged.connect(self.filter_results)
        search_boxes_layout.addWidget(self.package_id_search)

        self.description_search = QLineEdit(self)
        self.description_search.setPlaceholderText("Search Description")
        self.description_search.textChanged.connect(self.filter_results)
        search_boxes_layout.addWidget(self.description_search)

        left_layout.addLayout(search_boxes_layout)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        # Updated header labels with generic names
        self.result_table.setHorizontalHeaderLabels(["CustomerID", "IsActive", "PackageID", "Description", "Source"])
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)
        self.result_table.itemSelectionChanged.connect(self.result_table_selection_changed)
        left_layout.addWidget(self.result_table)

        search_info_textbox2 = QLineEdit(self)
        search_info_textbox2.setPlaceholderText("Search inside SubResult...")
        left_layout.addWidget(search_info_textbox2)

        self.info_textbox2 = QTextEdit(self)
        self.info_textbox2.setPlainText("SubResult")
        self.info_textbox2.setReadOnly(True)
        left_layout.addWidget(self.info_textbox2)

        content_layout.addLayout(left_layout)

        # Right side - detailed info panels
        right_layout = QGridLayout()

        # InfoBox3
        right_layout.addWidget(self.create_info_box("Infobox1", "Option1", "Option2", self.search_button_clicked_info3), 0, 0)
        # InfoBox4
        right_layout.addWidget(self.create_info_box("Infobox2", "Option1", "Option2", self.search_button_clicked_info4), 0, 1)

        content_layout.addLayout(right_layout)
        main_layout.addLayout(content_layout)

        # Load database configuration from config.ini
        self.load_database_config()

    def load_database_config(self):
        # Load database connection configuration from config.ini file
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.connection_config = {
            'host': config['database'].get('host', ''),
            'user': config['database'].get('user', ''),
            'password': config['database'].get('password', ''),
            'port': int(config['database'].get('port', 3306))
        }

    def create_info_box(self, placeholder, option1, option2, search_button_slot):
        # Create an information box with a combo box and a text field
        frame = QFrame()
        layout = QVBoxLayout()
        frame.setLayout(layout)

        combo_layout = QHBoxLayout()
        combo_box = QComboBox(self)
        combo_box.addItem(option1)
        combo_box.addItem(option2)
        combo_layout.addWidget(combo_box)

        search_button = QPushButton("Search", self)
        search_button.clicked.connect(search_button_slot)
        combo_layout.addWidget(search_button)

        layout.addLayout(combo_layout)

        info_table = QTableWidget()
        info_table.horizontalHeader().sectionClicked.connect(lambda index, table=info_table: self.header_clicked(index, table))
        layout.addWidget(info_table)

        if placeholder == "Infobox1":
            self.info_table1 = info_table
            self.combo_box_info3 = combo_box
        else:
            self.info_table2 = info_table
            self.combo_box_info4 = combo_box

        return frame

    @pyqtSlot()
    def search_textbox_keydown(self):
        # Handle search action when Enter key is pressed in the search textbox
        search_text = self.search_textbox.text()
        if search_text.isdigit():
            self.search_database_for_numeric_info(search_text)
        else:
            self.search_database_for_text_info(search_text)

    @pyqtSlot()
    def search_button_clicked_info3(self):
        # Handle search button click for InfoBox1
        self.search_button_clicked("Infobox1")

    @pyqtSlot()
    def search_button_clicked_info4(self):
        # Handle search button click for InfoBox2
        self.search_button_clicked("Infobox2")

    def search_button_clicked(self, infobox):
        # Perform search based on selection in combo box and display results in info box
        selected_items = self.result_table.selectedItems()
        if not selected_items:
            return

        selected_row = selected_items[0].row()
        package_id = self.result_table.item(selected_row, 2).text()

        if infobox == "Infobox1":
            selection = self.combo_box_info3.currentText()
        else:
            selection = self.combo_box_info4.currentText()

        self.handle_selection_async(selection, infobox, package_id)

    def result_table_selection_changed(self):
        # Handle result table selection change
        selected_items = self.result_table.selectedItems()
        if not selected_items:
            return

    def search_database_for_numeric_info(self, search_value):
        # Query the database for numeric search values (e.g., IDs)
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        # Update queries with generic table and column names
        query1 = """
            SELECT CustomerID, IsActive, PackageID, Description
            FROM DefaultTable1
            WHERE PackageID = %s OR CustomerID = %s;
        """

        query2 = """
            SELECT CustomerID, IsActive, PackageID, Description
            FROM DefaultTable2
            WHERE PackageID = %s OR CustomerID = %s;
        """

        query3 = """
            SELECT CustomerID, IsActive, PackageID, Description
            FROM DefaultTable3
            WHERE PackageID = %s OR CustomerID = %s;
        """

        try:
            cursor.execute(query1, (search_value, search_value))
            results1 = cursor.fetchall()

            cursor.execute(query2, (search_value, search_value))
            results2 = cursor.fetchall()

            cursor.execute(query3, (search_value, search_value))
            results3 = cursor.fetchall()

            self.result_table.setRowCount(0)

            if not results1 and not results2 and not results3:
                self.result_table.setRowCount(1)
                self.result_table.setItem(0, 0, QTableWidgetItem("No results found."))
            else:
                self.add_results_to_table(results1, "Source1")
                self.add_results_to_table(results2, "Source2")
                self.add_results_to_table(results3, "Source3")

            connection.commit()
        except Exception as e:
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("Error querying database. Check console for details."))
        finally:
            cursor.close()
            connection.close()

    def search_database_for_text_info(self, search_text):
        # Query the database for text search values (e.g., Descriptions)
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        # Update queries with generic table and column names
        query1 = """
            SELECT CustomerID, IsActive, PackageID, Description
            FROM DefaultTable1
            WHERE Description LIKE %s;
        """

        query2 = """
            SELECT CustomerID, IsActive, PackageID, Description
            FROM DefaultTable2
            WHERE Description LIKE %s;
        """

        query3 = """
            SELECT CustomerID, IsActive, PackageID, Description
            FROM DefaultTable3
            WHERE Description LIKE %s;
        """

        try:
            cursor.execute(query1, ('%' + search_text + '%',))
            results1 = cursor.fetchall()

            cursor.execute(query2, ('%' + search_text + '%',))
            results2 = cursor.fetchall()

            cursor.execute(query3, ('%' + search_text + '%',))
            results3 = cursor.fetchall()

            self.result_table.setRowCount(0)

            if not results1 and not results2 and not results3:
                self.result_table.setRowCount(1)
                self.result_table.setItem(0, 0, QTableWidgetItem("No results found."))
            else:
                self.add_results_to_table(results1, "Source1")
                self.add_results_to_table(results2, "Source2")
                self.add_results_to_table(results3, "Source3")

            connection.commit()
        except Exception as e:
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("Error querying database. Check console for details."))
        finally:
            cursor.close()
            connection.close()

    def add_results_to_table(self, results, source):
        # Add results from the query to the result table
        for row in results:
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            self.result_table.setItem(row_position, 0, QTableWidgetItem(str(row[0])))
            is_active = 'Yes' if row[1] == b'\x01' else 'No'
            self.result_table.setItem(row_position, 1, QTableWidgetItem(is_active))
            self.result_table.setItem(row_position, 2, QTableWidgetItem(str(row[2])))
            self.result_table.setItem(row_position, 3, QTableWidgetItem(str(row[3])))
            self.result_table.setItem(row_position, 4, QTableWidgetItem(source))

    def filter_results(self):
        # Filter results in the result table based on search text in the individual search boxes
        customer_id_filter = self.customer_id_search.text()
        is_active_filter = self.is_active_search.text().lower()
        package_id_filter = self.package_id_search.text()
        description_filter = self.description_search.text().lower()

        for row in range(self.result_table.rowCount()):
            customer_id_item = self.result_table.item(row, 0)
            is_active_item = self.result_table.item(row, 1)
            package_id_item = self.result_table.item(row, 2)
            description_item = self.result_table.item(row, 3)

            customer_id_visible = customer_id_filter in customer_id_item.text()
            is_active_visible = is_active_filter in is_active_item.text().lower()
            package_id_visible = package_id_filter in package_id_item.text()
            description_visible = description_filter in description_item.text().lower()

            is_row_visible = customer_id_visible and is_active_visible and package_id_visible and description_visible
            self.result_table.setRowHidden(row, not is_row_visible)

    def handle_selection_async(self, selection, infobox, package_id):
        # Handle selection change in combo boxes to query appropriate data
        if selection == "Option1":
            self.query_subscription_and_event_async("DefaultSubscriptionTable1", infobox, package_id)
        elif selection == "Option2":
            self.query_subscription_and_event_async("DefaultSubscriptionTable2", infobox, package_id)

    def query_subscription_and_event_async(self, subscription_table, infobox, package_id):
        # Query the subscription table for event IDs based on the search term
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            if subscription_table == "DefaultSubscriptionTable1":
                query = f"""
                    SELECT x.EventID, x.IsAutoAdded, x.IsDeleted, x.SubscriptionStatus, x.CreationDate, x.LastUpdate
                    FROM {subscription_table} x
                    WHERE x.PackageID = %s;
                """
                columns = ["EventID", "IsAutoAdded", "IsDeleted", "SubscriptionStatus", "CreationDate", "LastUpdate"]
            else:
                query = f"""
                    SELECT x.EventID, x.CreationDate
                    FROM {subscription_table} x
                    WHERE x.PackageID = %s;
                """
                columns = ["EventID", "CreationDate"]

            cursor.execute(query, (package_id,))
            results = cursor.fetchall()

            connection.commit()
        except pymysql.MySQLError as e:
            results = []
        except Exception as e:
            results = []
        finally:
            cursor.close()
            connection.close()

        self.display_results_in_infobox(results, infobox, columns)

    def display_results_in_infobox(self, results, infobox, columns):
        # Display the results in the appropriate info box
        info_table = self.info_table1 if infobox == "Infobox1" else self.info_table2
        info_table.setRowCount(0)
        info_table.setColumnCount(len(columns))
        info_table.setHorizontalHeaderLabels(columns)

        for row in results:
            row_position = info_table.rowCount()
            info_table.insertRow(row_position)
            for col_idx, col_val in enumerate(row):
                info_table.setItem(row_position, col_idx, QTableWidgetItem(str(col_val)))

    def header_clicked(self, logical_index, table_widget):
        # Handle header click for filtering results
        filter_value, ok = QInputDialog.getText(self, "Filter", f"Enter filter value for {table_widget.horizontalHeaderItem(logical_index).text()}:")
        if ok and filter_value:
            for row in range(table_widget.rowCount()):
                item = table_widget.item(row, logical_index)
                if filter_value.lower() not in item.text().lower():
                    table_widget.setRowHidden(row, True)
                else:
                    table_widget.setRowHidden(row, False)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
