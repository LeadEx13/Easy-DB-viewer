import sys
import pymysql
import configparser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QTextEdit,
                             QComboBox, QGridLayout, QFrame)
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
        self.search_textbox.setPlaceholderText("Main search")
        self.search_textbox.returnPressed.connect(self.search_textbox_keydown)
        main_layout.addWidget(self.search_textbox)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side - search results and subresults
        left_layout = QVBoxLayout()

        search_info_textbox1 = QLineEdit(self)
        search_info_textbox1.setPlaceholderText("Search inside Result...")
        left_layout.addWidget(search_info_textbox1)

        self.info_textbox1 = QTextEdit(self)
        self.info_textbox1.setPlainText("Result")
        self.info_textbox1.setReadOnly(True)
        left_layout.addWidget(self.info_textbox1)

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
        right_layout.addWidget(self.create_info_box("Infobox1", "Option1", "Option2", self.combobox_info3_selection_changed),
                               0, 0)
        # InfoBox4
        right_layout.addWidget(self.create_info_box("Infobox2", "Option1", "Option2", self.combobox_info4_selection_changed),
                               0, 1)

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
            'database': config['database']['database'],
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
        self.search_database_async(search_text, "DefaultTableName")

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

    def search_database_async(self, search_term, table_name):
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        # Query example. Adjust the query as per your table structure.
        query = """
            SELECT Id
            FROM DefaultTableName
            WHERE ColumnName = %s 
            AND DateColumn BETWEEN DATE_SUB(CURDATE(), INTERVAL 14 DAY) AND CURDATE();
        """

        try:
            cursor.execute(query, (search_term,))
            results = cursor.fetchall()

            self.info_textbox3.clear()

            if not results:
                self.info_textbox3.setPlainText("No results found.")
            else:
                for row in results:
                    self.info_textbox3.append(f"{row[0]}")

            connection.commit()
        except Exception as e:
            print(f"Error querying database: {e}")
            self.info_textbox3.setPlainText("Error querying database. Check console for details.")
        finally:
            cursor.close()
            connection.close()

    def handle_selection_async(self, selection, infobox):
        if selection == "Option1":
            self.query_subscription_and_event_async("SubscriptionTable", infobox)
        elif selection == "Option2":
            self.query_subscription_and_event_async("OtherSubscriptionTable", infobox)

    def query_subscription_and_event_async(self, subscription_table, infobox):
        search_term = self.search_textbox.text()
        connection = pymysql.connect(**self.connection_config)
        cursor = connection.cursor()

        event_ids = []

        try:
            cursor.execute(f"SELECT Id FROM `{subscription_table}` WHERE ColumnName = %s", (search_term,))
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
            cursor.execute("SELECT * FROM EventDetailsTable WHERE Id = %s", (event_id,))
            results = cursor.fetchall()

            for row in results:
                if infobox == "Infobox1":
                    self.info_textbox3.append(f"Event ID: {event_id}, Details: {row}")
                else:
                    self.info_textbox4.append(f"Event ID: {event_id}, Details: {row}")

            connection.commit()
        except Exception as e:
            print(f"Error querying Event details: {e}")
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
