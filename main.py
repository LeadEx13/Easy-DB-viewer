import sys
import os
import csv
import pymysql
import configparser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QTableWidget, QTableWidgetItem, QComboBox, QGridLayout, QFrame, QPushButton, QHeaderView, QInputDialog, QSizePolicy, QDateEdit, QDialog, QLabel, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import pyqtSlot, Qt, QDate
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
        self.setFixedSize(300, 100)  # Increased size for better visibility
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Loading...", self)
        self.layout.addWidget(self.label)

    def update_message(self, message):
        self.label.setText(message)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Easy DB viewer")
        self.setGeometry(100, 100, 1024, 720)

        self.loading_dialog = LoadingDialog(self)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # Top control area
        top_bar_layout = QHBoxLayout()
        main_layout.addLayout(top_bar_layout)

        self.search_textbox = QLineEdit(self)
        self.search_textbox.setPlaceholderText("Search by Id, CustomerId, or Description")
        self.search_textbox.setMaximumWidth(525)
        self.search_textbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.search_textbox.returnPressed.connect(self.search_textbox_keydown)
        top_bar_layout.addWidget(self.search_textbox)

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
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            "CustomerID", "Type", "PackageID", "Description",
            "Source", "Distribution", "IsActive", "ExpirationDate"
        ])
        header = self.result_table.horizontalHeader()
        for column in range(self.result_table.columnCount()):
            if column == 3:  # Assuming "Description" is the 4th column (index 3)
                header.setSectionResizeMode(column, QHeaderView.Fixed)
                header.resizeSection(column, 80)  # Set fixed width to 80
            else:
                header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

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
        self.sub_search_combo_box.addItem("Event Schedule")
        # Add more items as needed here...
        sub_search_layout.addWidget(self.sub_search_combo_box)

        self.sub_search_button = QPushButton("Search", self)
        self.sub_search_button.setMaximumWidth(100)
        self.sub_search_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.sub_search_button.clicked.connect(self.sub_search_button_clicked)
        sub_search_layout.addWidget(self.sub_search_button)

        self.export_button = QPushButton("Export", self)
        self.export_button.setMaximumWidth(100)
        self.export_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.export_button.clicked.connect(lambda: self.export_table_to_csv(self.sub_result_table, self.sub_search_combo_box.currentText()))
        sub_search_layout.addWidget(self.export_button)

        left_layout.addWidget(sub_search_container)

        self.sub_result_table = CustomTableWidget()
        self.sub_result_table.setMaximumWidth(525)
        left_layout.addWidget(self.sub_result_table)

        content_layout.addLayout(left_layout)

        # Right side - detailed info panels
        right_layout = QGridLayout()

        # InfoBox3
        right_layout.addWidget(self.create_info_box("Infobox1", "Option1", "Option2", "Option3", "Option4", "Option5", self.search_button_clicked_info3), 0, 0)
        # InfoBox4
        right_layout.addWidget(self.create_info_box("Infobox2", "Option1", "Option2", "Option3", "Option4", "Option5", self.search_button_clicked_info4), 0, 1)

        content_layout.addLayout(right_layout)
        main_layout.addLayout(content_layout)

        # Load database configuration from config.ini
        self.load_database_config()

        # Apply the dark mode initially
        self.set_dark_mode()

    def load_database_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.connection_config = {
            'host': config['database'].get('host', ''),
            'user': config['database'].get('user', ''),
            'password': config['database'].get('password', ''),
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
        search_button.setMaximumWidth(70)
        search_button.clicked.connect(search_button_slot)
        combo_layout.addWidget(search_button)

        export_button = QPushButton("Export", self)
        export_button.setMaximumWidth(70)
        combo_layout.addWidget(export_button)

        layout.addLayout(combo_layout)

        info_table = CustomTableWidget()
        layout.addWidget(info_table)

        if placeholder == "Infobox1":
            self.info_table1 = info_table
            self.combo_box_info3 = combo_box
            export_button.clicked.connect(lambda: self.export_table_to_csv(self.info_table1, self.combo_box_info3.currentText()))
        else:
            self.info_table2 = info_table
            self.combo_box_info4 = combo_box
            export_button.clicked.connect(lambda: self.export_table_to_csv(self.info_table2, self.combo_box_info4.currentText()))

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
        self.loading_dialog.update_message(f"Loading {selected_table}...")
        self.loading_dialog.show()

        if selected_table == "Event Schedule":
            self.query_event_schedule()
        # Add more elif clauses for other subsearch options

    def query_event_schedule(self):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT s.EventId, GROUP_CONCAT(DISTINCT s.ProviderId) AS ProviderIds, f.StartDate
                FROM default_event_schedule s
                JOIN default_events f ON s.EventId = f.Id
                WHERE f.StartDate > NOW()
                GROUP BY s.EventId, f.StartDate;
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

        self.loading_dialog.close()

    def search_database_for_numeric_info(self, search_value):
        self.loading_dialog.update_message("Loading search results...")
        self.loading_dialog.show()

        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        query1 = """
            SELECT CustomerId, IsActive, Id as PackageID, Description, ExpirationDate, DistributionEnabled as Distribution, Type
            FROM default_table1
            WHERE Id = %s OR CustomerId = %s;
        """

        query2 = """
            SELECT CustomerId, IsActive, Id as PackageID, Description, ExpirationDate, RmqEnabled as Distribution, HasInPlayOdds as Type
            FROM default_table2
            WHERE Id = %s OR CustomerId = %s;
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
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("Error querying database. Check console for details."))
        finally:
            cursor.close()
            connection.close()

        self.loading_dialog.close()

    def search_database_for_text_info(self, search_text):
        self.loading_dialog.update_message("Loading search results...")
        self.loading_dialog.show()

        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        query1 = """
            SELECT CustomerId, IsActive, Id as PackageID, Description, ExpirationDate, DistributionEnabled as Distribution, Type
            FROM default_table1
            WHERE Description LIKE %s;
        """

        query2 = """
            SELECT CustomerId, IsActive, Id as PackageID, Description, ExpirationDate, RmqEnabled as Distribution, HasInPlayOdds as Type
            FROM default_table2
            WHERE Description LIKE %s;
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
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("Error querying database. Check console for details."))
        finally:
            cursor.close()
            connection.close()

        self.loading_dialog.close()

    def add_results_to_table(self, results, source):
        for row in results:
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            self.result_table.setItem(row_position, 0, QTableWidgetItem(str(row[0])))  # CustomerID
            type_value = 'Live' if row[6] in [b'\x01', 1] else 'Pre-event'
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
        self.loading_dialog.update_message(f"Loading {selection} data...")
        self.loading_dialog.show()

        if selection == "Option1":
            self.query_subscription_and_fixture_async("default_table3", infobox, package_id)
        elif selection == "Option2":
            self.query_subscription_and_fixture_async("default_table4", infobox, package_id)
        elif selection == "Option3":
            self.query_web_notifications_async(infobox, package_id)
        elif selection == "Option4":
            self.query_subscriptions_async(infobox, package_id)
        elif selection == "Option5":
            self.query_customer_setting_changes_async(infobox, package_id)

    def export_table_to_csv(self, table, table_name):
        try:
            folder_path = os.path.join(os.path.expanduser("~"), "Documents", "Easy DB viewer")
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

    def query_subscription_and_fixture_async(self, subscription_table, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            if subscription_table == "default_table3":
                query = f"""
                    SELECT x.EventId as EventID, x.IsAutoAdded, x.IsDeleted, x.SubscriptionStatus, x.CreationDate, x.LastUpdate
                    FROM {subscription_table} x
                    JOIN default_events f ON x.EventId = f.Id
                    WHERE x.PackageId = %s AND f.StartDate > NOW() - INTERVAL 14 DAY;
                """
                columns = ["EventID", "IsAutoAdded", "IsDeleted", "SubscriptionStatus", "CreationDate", "LastUpdate"]
            else:
                query = f"""
                    SELECT x.EventId as EventID, x.CreationDate
                    FROM {subscription_table} x
                    JOIN default_events f ON x.EventId = f.Id
                    WHERE x.PackageId = %s AND f.StartDate > NOW() - INTERVAL 14 DAY;
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

    def query_web_notifications_async(self, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT Header, Body, CreationDate
                FROM default_webnotifications
                WHERE PackageId = %s AND CreationDate >= NOW() - INTERVAL 1 MONTH;
            """
            columns = ["Header", "Body", "CreationDate"]

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

    def query_subscriptions_async(self, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT SportId, LocationId, LeagueId, CreationDate, IsInPlay
                FROM default_subscriptions
                WHERE PackageId = %s AND CreationDate >= NOW() - INTERVAL 1 MONTH;
            """
            columns = ["SportId", "LocationId", "LeagueId", "CreationDate", "IsInPlay"]

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

    def query_customer_setting_changes_async(self, infobox, package_id):
        try:
            connection = pymysql.connect(**self.connection_config)
            cursor = connection.cursor()

            query = """
                SELECT ChangedID, ChangedField, NewValue, OldValue, CreationDate
                FROM default_setting_changes
                WHERE PackageId = %s AND CreationDate >= NOW() - INTERVAL 1 MONTH;
            """
            columns = ["ChangedID", "ChangedField", "NewValue", "OldValue", "CreationDate"]

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
                if columns[col_idx] in ["IsAutoAdded", "IsDeleted", "IsInPlay"]:
                    col_val = "Yes" if col_val == b'\x01' else "No"
                info_table.setItem(row_position, col_idx, QTableWidgetItem(str(col_val)))

        self.loading_dialog.close()

    #light mode that currently not in use
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
