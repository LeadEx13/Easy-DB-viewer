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
        self.search_textbox.setPlaceholderText("Search by Id")
        self.search_textbox.returnPressed.connect(self.search_textbox_keydown)
        main_layout.addWidget(self.search_textbox)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side - search results and subresults
        left_layout = QVBoxLayout()

        search_info_textbox1 = QLineEdit(self)
        search_info_textbox1.setPlaceholderText("Search inside Result...")
        left_layout.addWidget(search_info_textbox1)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        # Update header labels with generic names
        self.result_table.setHorizontalHeaderLabels(["ID", "Attribute1", "Attribute2", "Attribute3", "Description"])
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
        self.search_database_for_info(search_text)

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

    def search_database_for_info(self, search_id):
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        # Update queries with generic table and column names
        query1 = """
            SELECT ID, Attribute1, Attribute2
            FROM DefaultTable1
            WHERE ID = %s;
        """

        query2 = """
            SELECT Attribute3, Description
            FROM DefaultTable2
            WHERE ID = %s;
        """

        try:
            # Execute first query
            cursor.execute(query1, (search_id,))
            results1 = cursor.fetchall()

            # Execute second query
            cursor.execute(query2, (search_id,))
            results2 = cursor.fetchall()

            self.result_table.setRowCount(0)

            if not results1:
                self.result_table.setRowCount(1)
                self.result_table.setItem(0, 0, QTableWidgetItem("No results found."))
            else:
                for row in results1:
                    row_position = self.result_table.rowCount()
                    self.result_table.insertRow(row_position)
                    self.result_table.setItem(row_position, 0, QTableWidgetItem(str(row[0])))
                    self.result_table.setItem(row_position, 1, QTableWidgetItem(str(row[1])))
                    self.result_table.setItem(row_position, 2, QTableWidgetItem(str(row[2])))

                if results2:
                    for i, row in enumerate(results2):
                        self.result_table.setItem(i, 3, QTableWidgetItem(str(row[0])))
                        self.result_table.setItem(i, 4, QTableWidgetItem(str(row[1])))
                else:
                    for i in range(self.result_table.rowCount()):
                        self.result_table.setItem(i, 3, QTableWidgetItem("N/A"))
                        self.result_table.setItem(i, 4, QTableWidgetItem("N/A"))

            connection.commit()
        except Exception as e:
            print(f"Error querying database: {e}")
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("Error querying database. Check console for details."))
        finally:
            cursor.close()
            connection.close()

    def handle_selection_async(self, selection, infobox):
        # Handle selection changes in the comboboxes
        if selection == "Option1":
            self.query_subscription_and_fixture_async("DefaultTable1", infobox)
        elif selection == "Option2":
            self.query_subscription_and_fixture_async("DefaultTable2", infobox)

    def query_subscription_and_fixture_async(self, subscription_table, infobox):
        search_term = self.search_textbox.text()
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        fixture_ids = []

        try:
            cursor.execute(f"SELECT ID FROM {subscription_table} WHERE ID = %s", (search_term,))
            results = cursor.fetchall()

            fixture_ids = [row[0] for row in results]

            connection.commit()
        except Exception as e:
            print(f"Error querying database: {e}")
        finally:
            cursor.close()
            connection.close()

        for fixture_id in fixture_ids:
            self.query_fixture_details_async(fixture_id, infobox)

    def query_fixture_details_async(self, fixture_id, infobox):
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT * FROM DefaultTable3 WHERE ID = %s", (fixture_id,))
            results = cursor.fetchall()

            for row in results:
                if infobox == "Infobox1":
                    self.info_textbox3.append(f"Fixture ID: {fixture_id}, Details: {row}")
                else:
                    self.info_textbox4.append(f"Fixture ID: {fixture_id}, Details: {row}")

            connection.commit()
        except Exception as e:
            print(f"Error querying fixture details: {e}")
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
