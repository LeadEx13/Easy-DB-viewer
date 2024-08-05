import sys
import os
import csv
import pymysql
import configparser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QTableWidget, QTableWidgetItem, QComboBox, QGridLayout, QFrame, QPushButton, QHeaderView, QInputDialog, QSizePolicy, QDateEdit, QDialog, QLabel, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import pyqtSlot, Qt, QDate
from datetime import datetime

class CustomTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.handle_header_context_menu)

    def handle_header_context_menu(self, pos):
        logical_index = self.horizontalHeader().logicalIndexAt(pos)
        self.filter_column(logical_index)

    def filter_column(self, column):
        column_name = self.horizontalHeaderItem(column).text()
        if column_name in ["CreationDate", "LastUpdate", "StartDate"]:
            self.filter_by_date(column, column_name)
        else:
            filter_value, ok = QInputDialog.getText(self, "Filter", f"Enter filter value for {column_name}:")
            if ok:
                for row in range(self.rowCount()):
                    item = self.item(row, column)
                    if filter_value:
                        if filter_value.lower() not in item.text().lower():
                            self.setRowHidden(row, True)
                        else:
                            self.setRowHidden(row, False)
                    else:
                        self.setRowHidden(row, False)

    def filter_by_date(self, column, column_name):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Date")
        dialog_layout = QVBoxLayout()

        label = QLabel(f"Select a date for {column_name}:")
        dialog_layout.addWidget(label)

        date_edit = QDateEdit(dialog)
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        date_edit.setDisplayFormat("yyyy-MM-dd")
        dialog_layout.addWidget(date_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        dialog_layout.addWidget(button_box)

        dialog.setLayout(dialog_layout)

        if dialog.exec_() == QDialog.Accepted:
            filter_date = date_edit.date().toString("yyyy-MM-dd")
            for row in range(self.rowCount()):
                item = self.item(row, column)
                if filter_date not in item.text():
                    self.setRowHidden(row, True)
                else:
                    self.setRowHidden(row, False)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ez DB Search")
        self.setGeometry(100, 100, 1024, 720)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # Top control area
        self.search_textbox = QLineEdit(self)
        self.search_textbox.setPlaceholderText("Search by Id, CustomerId, or Description")
        self.search_textbox.setMaximumWidth(525)
        self.search_textbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.search_textbox.returnPressed.connect(self.search_textbox_keydown)
        main_layout.addWidget(self.search_textbox)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side - search results and subresults
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 10, 0)  # Add margin to the right side

        # Search boxes for each column
        search_boxes_layout = QHBoxLayout()
        search_boxes_container = QWidget()
        search_boxes_container.setMaximumWidth(525)
        search_boxes_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        search_boxes_container.setLayout(search_boxes_layout)

        self.customer_id_search = QLineEdit(self)
        self.customer_id_search.setPlaceholderText("Search CustomerID")
        self.customer_id_search.setMaximumWidth(525)
        self.customer_id_search.textChanged.connect(self.filter_results)
        search_boxes_layout.addWidget(self.customer_id_search)

        self.is_active_search = QLineEdit(self)
        self.is_active_search.setPlaceholderText("Search IsActive")
        self.is_active_search.setMaximumWidth(525)
        self.is_active_search.textChanged.connect(self.filter_results)
        search_boxes_layout.addWidget(self.is_active_search)

        self.package_id_search = QLineEdit(self)
        self.package_id_search.setPlaceholderText("Search PackageID")
        self.package_id_search.setMaximumWidth(525)
        self.package_id_search.textChanged.connect(self.filter_results)
        search_boxes_layout.addWidget(self.package_id_search)

        self.description_search = QLineEdit(self)
        self.description_search.setPlaceholderText("Search Description")
        self.description_search.setMaximumWidth(525)
        self.description_search.textChanged.connect(self.filter_results)
        search_boxes_layout.addWidget(self.description_search)

        left_layout.addWidget(search_boxes_container)

        # Main result table
        self.result_table = CustomTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["CustomerID", "IsActive", "PackageID", "Description", "Source"])
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)
        self.result_table.setMaximumWidth(525)
        self.result_table.itemSelectionChanged.connect(self.result_table_selection_changed)
        left_layout.addWidget(self.result_table)

        # Subresult search and box
        sub_search_layout = QHBoxLayout()
        sub_search_container = QWidget()
        sub_search_container.setMaximumWidth(525)
        sub_search_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sub_search_container.setLayout(sub_search_layout)

        self.sub_search_combo_box = QComboBox(self)
        self.sub_search_combo_box.addItem("Schedule")
        # Add more items as needed here...
        sub_search_layout.addWidget(self.sub_search_combo_box)

        self.sub_search_button = QPushButton("Search", self)
        self.sub_search_button.setMaximumWidth(70)
        self.sub_search_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.sub_search_button.clicked.connect(self.sub_search_button_clicked)
        sub_search_layout.addWidget(self.sub_search_button)

        self.export_sub_result_button = QPushButton("Export", self)
        self.export_sub_result_button.setMaximumWidth(70)
        self.export_sub_result_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.export_sub_result_button.clicked.connect(lambda: self.export_to_csv(self.sub_result_table, "SubResult"))
        sub_search_layout.addWidget(self.export_sub_result_button)

        left_layout.addWidget(sub_search_container)

        self.sub_result_table = CustomTableWidget()
        self.sub_result_table.setMaximumWidth(525)
        left_layout.addWidget(self.sub_result_table)

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
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.connection_config = {
            'host': config['database'].get('host', ''),
            'user': config['database'].get('user', ''),
            'password': config['database'].get('password', ''),
            'port': int(config['database'].get('port', 3306))
        }

    def create_info_box(self, placeholder, option1, option2, search_button_slot):
        frame = QFrame()
        layout = QVBoxLayout()
        frame.setLayout(layout)

        combo_layout = QHBoxLayout()
        combo_box = QComboBox(self)
        combo_box.addItem(option1)
        combo_box.addItem(option2)
        combo_layout.addWidget(combo_box)

        search_button = QPushButton("Search", self)
        search_button.setMaximumWidth(70)
        search_button.clicked.connect(search_button_slot)
        combo_layout.addWidget(search_button)

        export_button = QPushButton("Export", self)
        export_button.setMaximumWidth(70)
        export_button.clicked.connect(lambda: self.export_to_csv(self.info_table1 if placeholder == "Infobox1" else self.info_table2, f"{placeholder}_Result"))
        combo_layout.addWidget(export_button)

        layout.addLayout(combo_layout)

        info_table = CustomTableWidget()
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
        search_text = self.search_textbox.text()
        if search_text.isdigit():
            self.search_database_for_numeric_info(search_text)
        else:
            self.search_database_for_text_info(search_text)

    @pyqtSlot()
    def search_button_clicked_info3(self):
        self.search_button_clicked("Infobox1")

    @pyqtSlot()
    def search_button_clicked_info4(self):
        self.search_button_clicked("Infobox2")

    def search_button_clicked(self, infobox):
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
        selected_items = self.result_table.selectedItems()
        if not selected_items:
            return

    @pyqtSlot()
    def sub_search_button_clicked(self):
        selected_table = self.sub_search_combo_box.currentText()

        if selected_table == "Schedule":
            self.query_schedule()
        # Add more elif clauses for other subsearch options

    def query_schedule(self):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT s.EventID, GROUP_CONCAT(DISTINCT s.ProviderId) AS ProviderIds, f.StartDate
                FROM DefaultSubTable1 s
                JOIN DefaultMainTable f ON s.EventID = f.Id
                WHERE f.StartDate > NOW()
                GROUP BY s.EventID, f.StartDate;
            """
            cursor.execute(query)
            results = cursor.fetchall()

            connection.commit()

        except pymysql.MySQLError as e:
            results = []
        except Exception as e:
            results = []
        finally:
            cursor.close()
            connection.close()

        self.display_subsearch_results(results)

    def display_subsearch_results(self, results):
        self.sub_result_table.setRowCount(0)
        if not results:
            self.sub_result_table.setRowCount(1)
            self.sub_result_table.setItem(0, 0, QTableWidgetItem("No results found."))
            return

        columns = ["EventID", "ProviderIds", "StartDate"]
        self.sub_result_table.setColumnCount(len(columns))
        self.sub_result_table.setHorizontalHeaderLabels(columns)

        for row in results:
            row_position = self.sub_result_table.rowCount()
            self.sub_result_table.insertRow(row_position)
            for col_idx, col_val in enumerate(row):
                self.sub_result_table.setItem(row_position, col_idx, QTableWidgetItem(str(col_val)))

    def search_database_for_numeric_info(self, search_value):
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        query1 = """
            SELECT CustomerID, IsActive, PackageID, Description
            FROM DefaultTable1
            WHERE Id = %s OR CustomerID = %s;
        """

        query2 = """
            SELECT CustomerID, IsActive, PackageID, Description
            FROM DefaultTable2
            WHERE Id = %s OR CustomerID = %s;
        """

        query3 = """
            SELECT CustomerID, IsActive, PackageID, Description
            FROM DefaultTable3
            WHERE Id = %s OR CustomerID = %s;
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
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

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
        if selection == "Option1":
            self.query_subscription_and_event_async("DefaultSubscriptionTable1", infobox, package_id)
        elif selection == "Option2":
            self.query_subscription_and_event_async("DefaultSubscriptionTable2", infobox, package_id)

    def query_subscription_and_event_async(self, subscription_table, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            if subscription_table == "DefaultSubscriptionTable1":
                query = f"""
                    SELECT x.EventID, x.IsAutoAdded, x.IsDeleted, x.SubscriptionStatus, x.CreationDate, x.LastUpdate
                    FROM {subscription_table} x
                    JOIN DefaultEventTable f ON x.EventID = f.Id
                    WHERE x.PackageID = %s AND f.StartDate > NOW() - INTERVAL 14 DAY;
                """
                columns = ["EventID", "IsAutoAdded", "IsDeleted", "SubscriptionStatus", "CreationDate", "LastUpdate"]
            else:
                query = f"""
                    SELECT x.EventID, x.CreationDate
                    FROM {subscription_table} x
                    JOIN DefaultEventTable f ON x.EventID = f.Id
                    WHERE x.PackageID = %s AND f.StartDate > NOW() - INTERVAL 14 DAY;
                """
                columns = ["EventID", "CreationDate"]

            cursor.execute(query, (package_id,))
            filtered_results = cursor.fetchall()

            connection.commit()

        except pymysql.MySQLError as e:
            filtered_results = []
        except Exception as e:
            filtered_results = []
        finally:
            cursor.close()
            connection.close()

        self.display_results_in_infobox(filtered_results, infobox, columns)

    def display_results_in_infobox(self, results, infobox, columns):
        info_table = self.info_table1 if infobox == "Infobox1" else self.info_table2
        info_table.setRowCount(0)
        info_table.setColumnCount(len(columns))
        info_table.setHorizontalHeaderLabels(columns)

        for row in results:
            row_position = info_table.rowCount()
            info_table.insertRow(row_position)
            for col_idx, col_val in enumerate(row):
                if columns[col_idx] in ["IsAutoAdded", "IsDeleted"]:
                    col_val = "Yes" if col_val == b'\x01' else "No"
                info_table.setItem(row_position, col_idx, QTableWidgetItem(str(col_val)))

    def export_to_csv(self, table_widget, result_type):
        export_dir = os.path.join(os.path.expanduser("~"), "Documents", "Ez Search")
        os.makedirs(export_dir, exist_ok=True)

        current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result_type}_{current_datetime}.csv"
        filepath = os.path.join(export_dir, filename)

        with open(filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([table_widget.horizontalHeaderItem(i).text() for i in range(table_widget.columnCount())])
            for row in range(table_widget.rowCount()):
                writer.writerow([table_widget.item(row, col).text() for col in range(table_widget.columnCount())])

        QMessageBox.information(self, "Export Successful", f"Data exported to {filepath}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
