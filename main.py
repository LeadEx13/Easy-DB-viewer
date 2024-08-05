import sys
import pymysql
import configparser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QTextEdit,
                             QComboBox, QGridLayout, QFrame, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import pyqtSlot


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
        self.result_table.setColumnCount(4)
        # Updated header labels with generic names
        self.result_table.setHorizontalHeaderLabels(["CustomerID", "IsActive", "PackageID", "Description"])
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
        right_layout.addWidget(
            self.create_info_box("Infobox1", "Option1", "Option2", self.combobox_info3_selection_changed), 0, 0)
        # InfoBox4
        right_layout.addWidget(
            self.create_info_box("Infobox2", "Option1", "Option2", self.combobox_info4_selection_changed), 0, 1)

        content_layout.addLayout(right_layout)
        main_layout.addLayout(content_layout)

        # Load database configuration from config.ini
        self.load_database_config()

    def load_database_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.connection_config = {
            'host': config['database']['host'],
            'user': config['database']['user'],
            'password': config['database']['password'],
            'port': int(config['database']['port'])
        }

    def create_info_box(self, placeholder, option1, option2, selection_changed_slot):
        frame = QFrame()
        layout = QVBoxLayout()
        frame.setLayout(layout)

        combo_box = QComboBox(self)
        combo_box.addItem(option1)
        combo_box.addItem(option2)
        combo_box.currentTextChanged.connect(selection_changed_slot)
        layout.addWidget(combo_box)

        search_info_textbox = QLineEdit(self)
        search_info_textbox.setPlaceholderText(f"Search inside {placeholder}...")
        layout.addWidget(search_info_textbox)

        info_textbox = QTextEdit(self)
        info_textbox.setPlainText(f"Result {placeholder}")
        info_textbox.setReadOnly(True)
        layout.addWidget(info_textbox)

        if placeholder == "Infobox1":
            self.info_textbox3 = info_textbox
        else:
            self.info_textbox4 = info_textbox

        return frame

    @pyqtSlot()
    def search_textbox_keydown(self):
        search_text = self.search_textbox.text()
        print(f"Search triggered for: {search_text}")
        if search_text.isdigit():
            self.search_database_for_numeric_info(search_text)
        else:
            self.search_database_for_text_info(search_text)

    @pyqtSlot()
    def combobox_info3_selection_changed(self):
        selection = self.sender().currentText()
        print(f"Selection changed to: {selection}")
        self.handle_selection_async(selection, "Infobox1")

    @pyqtSlot()
    def combobox_info4_selection_changed(self):
        selection = self.sender().currentText()
        print(f"Selection changed to: {selection}")
        self.handle_selection_async(selection, "Infobox2")

    def search_database_for_numeric_info(self, search_value):
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
                self.add_results_to_table(results1)
                self.add_results_to_table(results2)

            connection.commit()
        except Exception as e:
            print(f"Error querying database: {e}")
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("Error querying database. Check console for details."))
        finally:
            cursor.close()
            connection.close()

    def search_database_for_text_info(self, search_text):
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
                self.add_results_to_table(results1)
                self.add_results_to_table(results2)

            connection.commit()
        except Exception as e:
            print(f"Error querying database: {e}")
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("Error querying database. Check console for details."))
        finally:
            cursor.close()
            connection.close()

    def add_results_to_table(self, results):
        for row in results:
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            self.result_table.setItem(row_position, 0, QTableWidgetItem(str(row[0])))
            is_active = 'Yes' if row[1] == b'\x01' else 'No'
            self.result_table.setItem(row_position, 1, QTableWidgetItem(is_active))
            self.result_table.setItem(row_position, 2, QTableWidgetItem(str(row[2])))
            self.result_table.setItem(row_position, 3, QTableWidgetItem(str(row[3])))

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

    def handle_selection_async(self, selection, infobox):
        if selection == "Option1":
            self.query_subscription_and_event_async("DefaultTable1", infobox)
        elif selection == "Option2":
            self.query_subscription_and_event_async("DefaultTable2", infobox)

    def query_subscription_and_event_async(self, subscription_table, infobox):
        search_term = self.search_textbox.text()
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        event_ids = []

        try:
            cursor.execute(f"SELECT EventID FROM {subscription_table} WHERE PackageID = %s", (search_term,))
            results = cursor.fetchall()

            event_ids = [row[0] for row in results]

            connection.commit()
        except Exception as e:
            print(f"Error querying database: {e}")
        finally:
            cursor.close()
            connection.close()

        for event_id in event_ids:
            self.query_event_details_async(event_id, infobox)

    def query_event_details_async(self, event_id, infobox):
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT * FROM DefaultTable3 WHERE EventID = %s", (event_id,))
            results = cursor.fetchall()

            for row in results:
                if infobox == "Infobox1":
                    self.info_textbox3.append(f"Event ID: {event_id}, Details: {row}")
                else:
                    self.info_textbox4.append(f"Event ID: {event_id}, Details: {row}")

            connection.commit()
        except Exception as e:
            print(f"Error querying event details: {e}")
        finally:
            cursor.close()
            connection.close()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
