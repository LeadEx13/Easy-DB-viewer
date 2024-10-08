import sys
import os
import csv
import pymysql
import configparser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QTableWidget,
                             QTableWidgetItem, QComboBox, QGridLayout, QFrame, QPushButton, QHeaderView, QInputDialog,
                             QSizePolicy, QDateEdit, QDialog, QLabel, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import pyqtSlot, Qt, QDate, QTimer
from PyQt5.QtGui import QIcon, QPalette, QColor
from datetime import datetime


class CustomTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSortingEnabled(True)

        # Enable context menu for right-click events
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.handle_header_context_menu)

    def handle_header_context_menu(self, pos):
        logical_index = self.horizontalHeader().logicalIndexAt(pos)
        self.filter_column(logical_index)

    def filter_column(self, column):
        column_name = self.horizontalHeaderItem(column).text()
        if column_name in ["Col1", "Col2", "Col3"]:
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
        dialog.setWindowTitle("Select Date Range")
        dialog_layout = QVBoxLayout()

        label = QLabel(f"Select a date range for {column_name}:")
        dialog_layout.addWidget(label)

        date_edit_from = QDateEdit(dialog)
        date_edit_from.setCalendarPopup(True)
        date_edit_from.setDate(QDate.currentDate().addMonths(-1))  # default to last month
        date_edit_from.setDisplayFormat("yyyy-MM-dd")
        dialog_layout.addWidget(QLabel("From:"))
        dialog_layout.addWidget(date_edit_from)

        date_edit_to = QDateEdit(dialog)
        date_edit_to.setCalendarPopup(True)
        date_edit_to.setDate(QDate.currentDate())
        date_edit_to.setDisplayFormat("yyyy-MM-dd")
        dialog_layout.addWidget(QLabel("To:"))
        dialog_layout.addWidget(date_edit_to)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        dialog_layout.addWidget(button_box)

        dialog.setLayout(dialog_layout)

        if dialog.exec_() == QDialog.Accepted:
            filter_date_from = date_edit_from.date()
            filter_date_to = date_edit_to.date()

            for row in range(self.rowCount()):
                item = self.item(row, column)
                if item:
                    date_text = item.text().split()[0]  # Consider only the date part
                    try:
                        date_value = QDate.fromString(date_text, "yyyy-MM-dd")
                        if filter_date_from <= date_value <= filter_date_to:
                            self.setRowHidden(row, False)
                        else:
                            self.setRowHidden(row, True)
                    except Exception as e:
                        print(f"Invalid date format in row {row}: {item.text()}")

    def sort_column(self, column):
        sort_order = self.horizontalHeader().sortIndicatorOrder()
        self.sortItems(column, sort_order)
        if sort_order == Qt.AscendingOrder:
            self.horizontalHeader().setSortIndicator(column, Qt.DescendingOrder)
        else:
            self.horizontalHeader().setSortIndicator(column, Qt.AscendingOrder)


class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading")
        self.setModal(True)
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Loading...", self)
        self.layout.addWidget(self.label)

    def update_message(self, message):
        self.label.setText(message)
        self.adjustSize()  # Adjust the dialog size based on the content


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ez DB search")
        self.setGeometry(100, 100, 1024, 720)
        # self.setWindowIcon(QIcon('icon.png'))

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        # Left side layout
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout)

        self.search_textbox = QLineEdit(self)
        self.search_textbox.setPlaceholderText("Search by Id, CustomerId, or Description")
        self.search_textbox.setMaximumWidth(525)
        self.search_textbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.search_textbox.returnPressed.connect(self.search_textbox_keydown)
        left_layout.addWidget(self.search_textbox)

        # Main result table
        self.result_table = CustomTableWidget()
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            "Col1", "Col2", "Col3", "Col4",
            "Col5", "Col6", "Col7", "Col8"
        ])
        header = self.result_table.horizontalHeader()
        for column in range(self.result_table.columnCount()):
            if column == 3:  # Assuming "Description" is the 4th column (index 3)
                header.setSectionResizeMode(column, QHeaderView.Fixed)
                header.resizeSection(column, 80)
            else:
                header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)
        self.result_table.setMaximumWidth(525)
        self.result_table.itemSelectionChanged.connect(self.result_table_selection_changed)
        left_layout.addWidget(self.result_table)

        self.main_loading_line = QLabel()
        self.main_loading_line.setFixedHeight(2)
        left_layout.addWidget(self.main_loading_line)

        # Subresult search and box
        sub_search_container = QWidget()
        sub_search_layout = QHBoxLayout()
        sub_search_container.setMaximumWidth(525)
        sub_search_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sub_search_container.setLayout(sub_search_layout)

        self.sub_search_combo_box = QComboBox(self)
        self.sub_search_combo_box.addItem("SubOption1")
        self.sub_search_combo_box.addItem("SubOption2")
        self.sub_search_combo_box.addItem("SubOption3")
        # Add more items as needed here...
        sub_search_layout.addWidget(self.sub_search_combo_box)

        self.sub_search_button = QPushButton("Search", self)
        self.sub_search_button.setIcon(QIcon('Search.png'))
        self.sub_search_button.setMaximumWidth(75)
        self.sub_search_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.sub_search_button.clicked.connect(self.sub_search_button_clicked)
        sub_search_layout.addWidget(self.sub_search_button)

        self.export_button = QPushButton("Export", self)
        self.export_button.setIcon(QIcon('Export.png'))
        self.export_button.setMaximumWidth(75)
        self.export_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.export_button.clicked.connect(
            lambda: self.export_table_to_csv(self.sub_result_table, self.sub_search_combo_box.currentText()))
        sub_search_layout.addWidget(self.export_button)

        left_layout.addWidget(sub_search_container)

        self.sub_result_table = CustomTableWidget()
        self.sub_result_table.setMaximumWidth(525)
        self.sub_result_table.setMaximumWidth(525)
        left_layout.addWidget(self.sub_result_table)

        self.sub_loading_line = QLabel()
        self.sub_loading_line.setFixedHeight(2)
        left_layout.addWidget(self.sub_loading_line)

        # Right side layout
        right_layout = QHBoxLayout()
        main_layout.addLayout(right_layout)

        right_layout.addWidget(
            self.create_info_box("Infobox1", "Option1", "Option2",
                                 "Option3", "Option4", "Option5",
                                 self.search_button_clicked_info3))
        right_layout.addWidget(
            self.create_info_box("Infobox2", "Option1", "Option2",
                                 "Option3", "Option4", "Option5",
                                 self.search_button_clicked_info4))

        # Load database configuration from config.ini
        self.load_database_config()

        # Apply the dark mode initially
        self.set_dark_mode()

    def load_database_config(self):
        config = configparser.ConfigParser()
        if hasattr(sys, '_MEIPASS'):
            config_path = os.path.join(sys._MEIPASS, 'config.ini')
        else:
            config_path = os.path.join(os.path.dirname(__file__), 'config.ini')

        config.read(config_path)

        # some of the DBs not use database as parameter to connect
        if 'database' not in config:
            raise KeyError("Config file is missing the 'database' section")

        self.connection_config = {
            'host': config['database'].get('host', ''),
            'user': config['database'].get('user', ''),
            'password': config['database'].get('password', ''),
            'database': config['database'].get('database', ''),
            'port': int(config['database'].get('port', 3306))
        }

    def create_info_box(self, placeholder, option1, option2, option3, option4, option5, search_button_slot):
        frame = QFrame()
        layout = QVBoxLayout()
        frame.setLayout(layout)

        combo_layout = QHBoxLayout()
        combo_box = QComboBox(self)
        combo_box.addItem(option1)
        combo_box.addItem(option2)
        combo_box.addItem(option3)
        combo_box.addItem(option4)
        combo_box.addItem(option5)
        combo_layout.addWidget(combo_box)

        search_button = QPushButton("Search", self)
        search_button.setIcon(QIcon('Search.png'))
        search_button.setMaximumWidth(75)
        search_button.clicked.connect(search_button_slot)
        combo_layout.addWidget(search_button)

        export_button = QPushButton("Export", self)
        export_button.setIcon(QIcon('Export.png'))
        export_button.setMaximumWidth(75)
        combo_layout.addWidget(export_button)

        layout.addLayout(combo_layout)

        info_table = CustomTableWidget()
        layout.addWidget(info_table)

        loading_line = QLabel()
        loading_line.setFixedHeight(2)
        layout.addWidget(loading_line)

        if placeholder == "Infobox1":
            self.info_table1 = info_table
            self.combo_box_info3 = combo_box
            self.info_loading_line1 = loading_line
            export_button.clicked.connect(
                lambda: self.export_table_to_csv(self.info_table1, self.combo_box_info3.currentText()))
        else:
            self.info_table2 = info_table
            self.combo_box_info4 = combo_box
            self.info_loading_line2 = loading_line
            export_button.clicked.connect(
                lambda: self.export_table_to_csv(self.info_table2, self.combo_box_info4.currentText()))

        # Adjust columns based on the text in these specific fields
        adjust_columns = ["Col1", "Col2", "Col3", "Col4", "Col5", "Col6", "Col7",
                          "Col8", "Col9", "Col10", "Col11"]
        for i in range(info_table.columnCount()):
            if info_table.horizontalHeaderItem(i).text() in adjust_columns:
                info_table.resizeColumnToContents(i)

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
        self.set_loading_line(self.sub_loading_line, True)
        QTimer.singleShot(1000, lambda: self.query_sub_search_data(selected_table))

    def query_sub_search_data(self, selected_table):
        if selected_table == "SubOption1":
            self.query_sub_option1()
        elif selected_table == "SubOption2":
            self.query_sub_option2()
        elif selected_table == "SubOption3":
            self.query_sub_option3()
        # Add more elif clauses for other subsearch options

    def query_sub_option1(self):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT s.Col1, GROUP_CONCAT(DISTINCT s.Col2) AS Col2, f.Col3
                FROM table1 s
                JOIN table2 f ON s.Col1 = f.Col1
                WHERE f.Col3 > NOW()
                GROUP BY s.Col1, f.Col3;
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

    def query_sub_option2(self):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT Col1, Col2, Col3, Col4
                FROM table3;
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

        self.display_subsearch_results_providers(results)

    def query_sub_option3(self):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT Col1, Col2, Col3
                FROM table4;
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

        self.display_subsearch_results_languages(results)

    def display_subsearch_results(self, results):
        self.sub_result_table.setRowCount(0)
        if not results:
            self.sub_result_table.setRowCount(1)
            self.sub_result_table.setItem(0, 0, QTableWidgetItem("No results found."))
            self.set_loading_line(self.sub_loading_line, False)
            return

        columns = ["Col1", "Col2", "Col3"]
        self.sub_result_table.setColumnCount(len(columns))
        self.sub_result_table.setHorizontalHeaderLabels(columns)

        for row in results:
            row_position = self.sub_result_table.rowCount()
            self.sub_result_table.insertRow(row_position)
            for col_idx, col_val in enumerate(row):
                self.sub_result_table.setItem(row_position, col_idx, QTableWidgetItem(str(col_val)))

        self.set_loading_line(self.sub_loading_line, False)

    def display_subsearch_results_providers(self, results):
        self.sub_result_table.setRowCount(0)
        if not results:
            self.sub_result_table.setRowCount(1)
            self.sub_result_table.setItem(0, 0, QTableWidgetItem("No results found."))
            self.set_loading_line(self.sub_loading_line, False)
            return

        columns = ["Col1", "Col2", "Col3", "Col4"]
        self.sub_result_table.setColumnCount(len(columns))
        self.sub_result_table.setHorizontalHeaderLabels(columns)

        for row in results:
            row_position = self.sub_result_table.rowCount()
            self.sub_result_table.insertRow(row_position)
            for col_idx, col_val in enumerate(row):
                if columns[col_idx] in ["Col2", "Col3", "Col4"]:
                    col_val = "Yes" if col_val == b'\x01' else "Yes" if col_val == 1 else "No"
                self.sub_result_table.setItem(row_position, col_idx, QTableWidgetItem(str(col_val)))

        self.set_loading_line(self.sub_loading_line, False)

    def display_subsearch_results_languages(self, results):
        self.sub_result_table.setRowCount(0)
        if not results:
            self.sub_result_table.setRowCount(1)
            self.sub_result_table.setItem(0, 0, QTableWidgetItem("No results found."))
            self.set_loading_line(self.sub_loading_line, False)
            return

        columns = ["Col1", "Col2", "Col3"]
        self.sub_result_table.setColumnCount(len(columns))
        self.sub_result_table.setHorizontalHeaderLabels(columns)

        for row in results:
            row_position = self.sub_result_table.rowCount()
            self.sub_result_table.insertRow(row_position)
            for col_idx, col_val in enumerate(row):
                self.sub_result_table.setItem(row_position, col_idx, QTableWidgetItem(str(col_val)))

        self.set_loading_line(self.sub_loading_line, False)

    def search_database_for_numeric_info(self, search_value):
        self.set_loading_line(self.main_loading_line, True)
        QTimer.singleShot(1000, lambda: self.query_numeric_info(search_value))

    def query_numeric_info(self, search_value):
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        query1 = """
            SELECT Col1, Col2, Col3, Col4, Col5, Col6, Col7
            FROM table5
            WHERE Col3 = %s OR Col1 = %s;
        """

        query2 = """
            SELECT Col1, Col2, Col3, Col4, Col5, Col6, Col7
            FROM table6
            WHERE Col3 = %s OR Col1 = %s;
        """

        try:
            cursor.execute(query1, (search_value, search_value))
            results1 = cursor.fetchall()

            cursor.execute(query2, (search_value, search_value))
            results2 = cursor.fetchall()

            self.result_table.setRowCount(0)

            if not results1 and not results2:
                self.result_table.setRowCount(1)
                self.result_table.setItem(0, 0, QTableWidgetItem("No results found."))
            else:
                self.add_results_to_table(results1, "Source1")
                self.add_results_to_table(results2, "Source2")

            connection.commit()
        except Exception as e:
            print(f"Error querying database: {e}")
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("Error querying database. Check console for details."))
        finally:
            cursor.close()
            connection.close()

        self.set_loading_line(self.main_loading_line, False)

    def search_database_for_text_info(self, search_text):
        self.set_loading_line(self.main_loading_line, True)
        QTimer.singleShot(1000, lambda: self.query_text_info(search_text))

    def query_text_info(self, search_text):
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        query1 = """
            SELECT Col1, Col2, Col3, Col4, Col5, Col6, Col7
            FROM table5
            WHERE Col4 LIKE %s;
        """

        query2 = """
            SELECT Col1, Col2, Col3, Col4, Col5, Col6, Col7
            FROM table6
            WHERE Col4 LIKE %s;
        """

        try:
            cursor.execute(query1, ('%' + search_text + '%',))
            results1 = cursor.fetchall()

            cursor.execute(query2, ('%' + search_text + '%',))
            results2 = cursor.fetchall()

            self.result_table.setRowCount(0)

            if not results1 and not results2:
                self.result_table.setRowCount(1)
                self.result_table.setItem(0, 0, QTableWidgetItem("No results found."))
            else:
                self.add_results_to_table(results1, "Source1")
                self.add_results_to_table(results2, "Source2")

            connection.commit()
        except Exception as e:
            print(f"Error querying database: {e}")
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("Error querying database. Check console for details."))
        finally:
            cursor.close()
            connection.close()

        self.set_loading_line(self.main_loading_line, False)

    def add_results_to_table(self, results, source):
        for row in results:
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            self.result_table.setItem(row_position, 0, QTableWidgetItem(str(row[0])))  # CustomerID
            type_value = 'Yes' if row[6] in [b'\x01', 1] else 'No'
            self.result_table.setItem(row_position, 1, QTableWidgetItem(type_value))  # Type
            self.result_table.setItem(row_position, 2, QTableWidgetItem(str(row[2])))  # PackageID
            self.result_table.setItem(row_position, 3, QTableWidgetItem(str(row[3])))  # Description
            self.result_table.setItem(row_position, 4, QTableWidgetItem(source))  # Source
            distribution_value = 'Yes' if row[5] == b'\x01' else 'No'
            self.result_table.setItem(row_position, 5, QTableWidgetItem(distribution_value))  # Distribution
            is_active = 'Yes' if row[1] == b'\x01' else 'No'
            self.result_table.setItem(row_position, 6, QTableWidgetItem(is_active))  # IsActive
            self.result_table.setItem(row_position, 7, QTableWidgetItem(str(row[4])))  # ExpirationDate

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
        self.set_loading_line(self.info_loading_line1 if infobox == "Infobox1" else self.info_loading_line2, True)
        QTimer.singleShot(1000, lambda: self.query_selection_async(selection, infobox, package_id))

    def query_selection_async(self, selection, infobox, package_id):
        if selection == "Option1":
            self.query_option1_async("table7", infobox, package_id)
        elif selection == "Option2":
            self.query_option2_async(infobox, package_id)
        elif selection == "Option3":
            self.query_option3_async(infobox, package_id)
        elif selection == "Option4":
            self.query_option4_async(infobox, package_id)
        elif selection == "Option5":
            self.query_option5_async(infobox, package_id)

    def export_table_to_csv(self, table, table_name):
        try:
            folder_path = os.path.join(os.path.expanduser("~"), "Documents", "Ez Search")
            os.makedirs(folder_path, exist_ok=True)
            file_name = f"{table_name}_export_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
            file_path = os.path.join(folder_path, file_name)

            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                header = [table.horizontalHeaderItem(col).text() for col in range(table.columnCount())]
                writer.writerow(header)
                for row in range(table.rowCount()):
                    if table.isRowHidden(row):
                        continue  # Skip hidden rows
                    row_data = [table.item(row, col).text() if table.item(row, col) else '' for col in
                                range(table.columnCount())]
                    writer.writerow(row_data)

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Export Successful\nFile saved to: {file_path}")
            msg.setWindowTitle("Export Status")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Open)
            if msg.exec_() == QMessageBox.Open:
                os.startfile(folder_path)

        except Exception as e:
            print(f"Export error: {e}")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(f"Export Failed\nError: {str(e)}")
            msg.setWindowTitle("Export Status")
            msg.exec_()

    def query_option1_async(self, subscription_table, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            if subscription_table == "table7":
                query = f"""
                    SELECT x.Col1 as Col1, x.Col2, x.Col3, x.Col4, x.Col5, x.Col6
                    FROM {subscription_table} x
                    JOIN table2 f ON x.Col1 = f.Col1
                    WHERE x.Col3 = %s AND f.Col3 > NOW() - INTERVAL 14 DAY;
                """
                columns = ["Col1", "Col2", "Col3", "Col4", "Col5", "Col6"]
            else:
                query = f"""
                    SELECT x.Col1 as Col1, x.Col5
                    FROM {subscription_table} x
                    JOIN table2 f ON x.Col1 = f.Col1
                    WHERE x.Col3 = %s AND f.Col3 > NOW() - INTERVAL 14 DAY;
                """
                columns = ["Col1", "Col5"]

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

        if not filtered_results:
            filtered_results = [(None,)] * len(columns)
            filtered_results[0] = (f"No data available within the last 14 days",)

        self.display_results_in_infobox(filtered_results, infobox, columns)

    def query_option2_async(self, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            # Query table8
            query_prematch = """
                SELECT Col1, Col5
                FROM table8
                WHERE Col3 = %s;
            """
            cursor.execute(query_prematch, (package_id,))
            prematch_results = cursor.fetchall()

            # Query table9
            query_subscriptions = """
                SELECT Col2, Col3, Col4, Col5
                FROM table9
                WHERE Col3 = %s;
            """
            cursor.execute(query_subscriptions, (package_id,))
            subscriptions_results = cursor.fetchall()

            combined_results = []

            # Add table8 results with level "Fixture"
            for row in prematch_results:
                combined_results.append((*row, 'Fixture'))

            # Add fixtures from table9 with appropriate level
            for row in subscriptions_results:
                col2, col3, col4, col5 = row

                if col4:
                    query_fixtures = """
                        SELECT Col1, Col5
                        FROM table2
                        WHERE Col4 = %s AND Col5 > NOW() - INTERVAL 5 DAY AND Col6 NOT IN (10, 7, 4);
                    """
                    cursor.execute(query_fixtures, (col4,))
                    fixtures = cursor.fetchall()
                    for fixture in fixtures:
                        fixture_id, start_date = fixture
                        combined_results.append((fixture_id, max(start_date, col5), 'League'))

                elif col3:
                    query_fixtures = """
                        SELECT Col1, Col5
                        FROM table2
                        WHERE Col3 = %s AND Col2 = %s AND Col5 > NOW() - INTERVAL 5 DAY AND Col6 NOT IN (10, 7, 4);
                    """
                    cursor.execute(query_fixtures, (col3, col2))
                    fixtures = cursor.fetchall()
                    for fixture in fixtures:
                        fixture_id, start_date = fixture
                        combined_results.append((fixture_id, max(start_date, col5), 'Location'))

                elif col2:
                    query_fixtures = """
                        SELECT Col1, Col5
                        FROM table2
                        WHERE Col2 = %s AND Col5 > NOW() - INTERVAL 5 DAY AND Col6 NOT IN (10, 7, 4);
                    """
                    cursor.execute(query_fixtures, (col2,))
                    fixtures = cursor.fetchall()
                    for fixture in fixtures:
                        fixture_id, start_date = fixture
                        combined_results.append((fixture_id, max(start_date, col5), 'Sport'))

            connection.commit()

        except pymysql.MySQLError as e:
            print(f"MySQL error: {e}")
            combined_results = []
        except Exception as e:
            print(f"Exception: {e}")
            combined_results = []
        finally:
            cursor.close()
            connection.close()

        if not combined_results:
            combined_results = [(None, None, "No data available")]

        self.display_results_in_infobox(combined_results, infobox, ["Col1", "Col5", "Level"])

    def query_option3_async(self, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT Col1, Col2, Col5
                FROM table10
                WHERE Col3 = %s AND Col5 >= NOW() - INTERVAL 14 DAY;
            """
            columns = ["Col1", "Col2", "Col5"]

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

        if not filtered_results:
            filtered_results = [(None, None, None)]
            filtered_results[0] = ("No data available within the last 14 days",)

        self.display_results_in_infobox(filtered_results, infobox, columns)

    def query_option4_async(self, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT Col2, Col3, Col4, Col5, Col6
                FROM table9
                WHERE Col3 = %s AND Col5 >= NOW() - INTERVAL 14 DAY;
            """
            columns = ["Col2", "Col3", "Col4", "Col5", "Col6"]

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

        if not filtered_results:
            filtered_results = [(None, None, None, None, None)]
            filtered_results[0] = ("No data available within the last 14 days",)

        self.display_results_in_infobox(filtered_results, infobox, columns)

    def query_option5_async(self, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT Col1, Col2, Col3, Col4, Col5
                FROM table11
                WHERE Col3 = %s AND Col5 >= NOW() - INTERVAL 14 DAY;
            """
            columns = ["Col1", "Col2", "Col3", "Col4", "Col5"]

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

        if not filtered_results:
            filtered_results = [(None, None, None, None, None)]
            filtered_results[0] = ("No data available within the last 14 days",)

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
                if columns[col_idx] in ["Col2", "Col3", "Col6"]:
                    col_val = "Yes" if col_val == b'\x01' else "No"
                info_table.setItem(row_position, col_idx,
                                   QTableWidgetItem(str(col_val) if col_val is not None else "No data available"))

        self.set_loading_line(self.info_loading_line1 if infobox == "Infobox1" else self.info_loading_line2, False)

    def set_loading_line(self, line_label, loading):
        if loading:
            line_label.setStyleSheet("background-color: red;")
        else:
            line_label.setStyleSheet("background-color: green;")

    def set_light_mode(self):
        app.setStyle('Fusion')
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ToolTipBase, Qt.black)
        palette.setColor(QPalette.ToolTipText, Qt.black)
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)

    def set_dark_mode(self):
        app.setStyle('Fusion')
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)


def main():
    global app
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
