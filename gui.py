from PyQt5.QtWidgets import *
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from authServer import authenticate
import json
import sys

app = QApplication(sys.argv)
window = QWidget()
window.setFixedSize(700, 700)
window.setWindowTitle("Login & Sign Up")

window.setStyleSheet("""
    QWidget {
        background-color: qlineargradient(
            spread:pad, x1:0, y1:0, x2:1, y2:1,
            stop:0 #dce9ff, stop:1 #b8dfff
        );
    }

    QTabWidget::pane {
        border: 2px solid #003366;
        border-radius: 10px;
        background: #e6f0ff;
    }

    QTabBar::tab {
        background: #99c2ff;
        color: #002244;
        padding: 10px 20px;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
        font-weight: bold;
        font-size: 13px;
    }

    QTabBar::tab:selected {
        background: #002244;
        color: white;
    }

    QFrame {
        background-color: #f4f9ff;
        border-radius: 12px;
        padding: 15px;
        border: 2px solid #99c2ff;
    }

    QLabel {
        color: #002244;
        font-size: 14px;
        font-weight: bold;
    }

    QLineEdit {
        background-color: white;
        border: 1px solid #99c2ff;
        border-radius: 6px;
        padding: 6px;
        color: #002244;
        selection-color: white;
        selection-background-color: #004080;
        font-size: 13px;
    }

    QPushButton {
        background-color: #002244;
        color: white;
        border-radius: 8px;
        padding: 8px 12px;
        font-weight: bold;
        font-size: 13px;
    }

    QPushButton:hover {
        background-color: #004080;
    }

    QComboBox {
        background-color: white;
        border: 1px solid #99c2ff;
        border-radius: 6px;
        padding: 5px;
        color: #002244;
        font-size: 13px;
    }

    QComboBox QAbstractItemView {
        background-color: #f4f9ff;
        selection-background-color: #004080;
        selection-color: white;
    }

    QLabel#error {
        color: red;
        font-weight: bold;
        font-size: 13px;
    }
""")


tabs = QTabWidget()
tabs.setTabPosition(QTabWidget.North)
tabs.setStyleSheet("QTabWidget::tab-bar { alignment: center; }")

# Login tab

login_tab = QWidget()
login_layout_1 = QVBoxLayout()

login_form_frame = QFrame()
login_layout = QVBoxLayout()

login_header_lbl = QLabel("Welcome Back !")
login_layout.addWidget(login_header_lbl, alignment=Qt.AlignCenter)


# The username label and box
login_user_lbl = QLabel("Username : ")
login_user_box = QLineEdit()
login_user_box.setPlaceholderText("What's before @ in your aub email")

# To make the label and the box on the same line we create a Horizontal layout
login_username_layout = QHBoxLayout()
login_username_layout.addWidget(login_user_lbl)
login_username_layout.addWidget(login_user_box)

# add this horizontal layout to the login tab
login_layout.addLayout(login_username_layout)

# The Password label and box
login_pass_lbl = QLabel("Password : ")
login_pass_box = QLineEdit()
login_pass_box.setPlaceholderText("Enter password")
login_pass_box.setEchoMode(QLineEdit.Password)  # hides text

login_pass_showbtn = QPushButton("Show")

def showtextlogin():
    # toggle password visibility
    if login_pass_box.echoMode() == QLineEdit.Normal:
        login_pass_box.setEchoMode(QLineEdit.Password)
    else:
        login_pass_box.setEchoMode(QLineEdit.Normal)

login_pass_showbtn.clicked.connect(showtextlogin)

# To make the label and the box on the same line we create a Horizontal layout
login_password_layout = QHBoxLayout()
login_password_layout.addWidget(login_pass_lbl)
login_password_layout.addWidget(login_pass_box)
login_password_layout.addWidget(login_pass_showbtn)

# add this horizontal layout to the login tab
login_layout.addLayout(login_password_layout)

# add a label so that if i need to display any error i display it here

login_error_lbl = QLabel("")
login_error_lbl.setObjectName("error")
login_layout.addWidget(login_error_lbl, alignment=Qt.AlignCenter)

# add a login button and it's functionalities 

def login():
    username_txt = login_user_box.text().strip()
    password_txt = login_pass_box.text().strip()


    if username_txt and password_txt:

        login_data = {
            "type_of_connection": "login",
            "userName": username_txt,
            "password": password_txt
        }

        try:
            # Convert to JSON string
            json_data = json.dumps(login_data)
            print(f"Sending JSON: {json_data}")
            
            # Send to the authentication server
            response = authenticate(json_data)
            
            # Handle the response from the auth server
            if response.get("status") == "200":
                login_error_lbl.setStyleSheet("color: green; font-weight: bold;")
                login_error_lbl.setText("Login successful!")
                print(f"Welcome! Email: {response.get('email')}")
            else:
                login_error_lbl.setStyleSheet("color: red; font-weight: bold;")
                login_error_lbl.setText(response.get("message"))
                
        except Exception as e:
            login_error_lbl.setStyleSheet("color: red; font-weight: bold;")
            login_error_lbl.setText(f"Connection error: {str(e)}")

        print("Sent a request to the server")
    else:
        login_error_lbl.setStyleSheet("color: red; font-weight: bold;")
        login_error_lbl.setText("Please fill all the fields.")

login_logbtn = QPushButton("Login")
login_logbtn.clicked.connect(login)

login_layout.addWidget(login_logbtn)

login_form_frame.setLayout(login_layout)
login_layout_1.addWidget(login_form_frame)
login_tab.setLayout(login_layout_1)


tabs.addTab(login_tab, "Login")



##########################
##########################

# Sign up tab

signup_tab = QWidget()
signup_layout_1 = QVBoxLayout()

signup_form_frame = QFrame()
signup_layout = QVBoxLayout()

# header label in my signup page
signup_header_lbl = QLabel("Create a new account : ")
signup_header_lbl.setFont(QFont("Times New Roman",20))
signup_layout.addWidget(signup_header_lbl, alignment=Qt.AlignCenter)

# the full name horizontal layout
signup_fullname_layout = QHBoxLayout()
signup_fullname_lbl = QLabel("Full Name : ")
signup_fullname_box = QLineEdit()
signup_fullname_box.setPlaceholderText("Ex : Ali Abdul Sater")

signup_fullname_layout.addWidget(signup_fullname_lbl)
signup_fullname_layout.addWidget(signup_fullname_box)

signup_layout.addLayout(signup_fullname_layout)

# the email horizontal layout
signup_email_layout = QHBoxLayout()
signup_email_lbl = QLabel("Email : ")
signup_email_box = QLineEdit()
signup_email_box.setPlaceholderText("Enter aub email : @mail.aub.edu / @aub.edu.lb")

signup_email_layout.addWidget(signup_email_lbl)
signup_email_layout.addWidget(signup_email_box)

signup_layout.addLayout(signup_email_layout)

# the username horizontal layout
signup_username_layout = QHBoxLayout()
signup_username_lbl = QLabel("username : ")
signup_username_box = QLineEdit()
signup_username_box.setPlaceholderText("What's before @ in your aub email")

signup_username_layout.addWidget(signup_username_lbl)
signup_username_layout.addWidget(signup_username_box)

signup_layout.addLayout(signup_username_layout)

# the password horizontal layout 
signup_pass_lbl = QLabel("Password : ")
signup_pass_box = QLineEdit()
signup_pass_box.setPlaceholderText("Enter password")
signup_pass_box.setEchoMode(QLineEdit.Password)  # hides text
signup_pass_showbtn = QPushButton("Show")

def showtextsignup():
    # toggle password visibility
    if signup_pass_box.echoMode() == QLineEdit.Normal:
        signup_pass_box.setEchoMode(QLineEdit.Password)
    else:
        signup_pass_box.setEchoMode(QLineEdit.Normal)

signup_pass_showbtn.clicked.connect(showtextsignup)

signup_password_layout = QHBoxLayout()
signup_password_layout.addWidget(signup_pass_lbl)
signup_password_layout.addWidget(signup_pass_box)
signup_password_layout.addWidget(signup_pass_showbtn)

signup_layout.addLayout(signup_password_layout)

# the Role horizontal layout
signup_role_layout = QHBoxLayout()
signup_role_lbl = QLabel("Role : ")
signup_role_combobox = QComboBox(editable = True, insertPolicy = QComboBox.InsertAtTop)
signup_role_combobox.addItems(["Driver", "Passenger"])

signup_role_layout.addWidget(signup_role_lbl)
signup_role_layout.addWidget(signup_role_combobox)

signup_layout.addLayout(signup_role_layout)

# The Area horizontal layour
signup_area_layout = QHBoxLayout()
signup_area_lbl = QLabel("Area : ")
signup_area_combobox = QComboBox(editable = True, insertPolicy = QComboBox.InsertAtTop)
signup_area_combobox.addItems(["Dahyeh", "Haret Hreik", "Khaldeh", "Jbeil", "Baalback", "Chwayfet", "Baabda", "Mansouriyeh", "Nabatiyeh", "Tyre", "Tripoli", "Hermel"])

signup_area_layout.addWidget(signup_area_lbl)
signup_area_layout.addWidget(signup_area_combobox)

signup_layout.addLayout(signup_area_layout)

# add a label so that if i need to display any error i display it here

signup_error_lbl = QLabel("")
signup_error_lbl.setObjectName("error")
signup_layout.addWidget(signup_error_lbl, alignment=Qt.AlignCenter)

# add a login button and it's functionalities 

def signup():
    fullname_txt = signup_fullname_box.text().strip()
    email_txt = signup_email_box.text().strip()
    username_txt = signup_username_box.text().strip()
    password_txt = signup_pass_box.text().strip()
    role_txt = signup_role_combobox.currentText().strip()
    area_txt = signup_area_combobox.currentText().strip()

    if fullname_txt and email_txt and username_txt and password_txt and role_txt and area_txt:

        signup_data = {
            "type_of_connection": "signUp",
            "userName": username_txt,
            "password": password_txt,
            "email" : email_txt,
            "isDriver" : role_txt == "Driver",
            "aubID" : "202500049"
        }

        try:
            # Convert to JSON string
            json_data = json.dumps(signup_data)
            print(f"Sending JSON: {json_data}")
            
            # Send to the authentication server
            response = authenticate(json_data)
            
            # Handle the response from the auth server
            if response.get("status") == "201":
                signup_error_lbl.setStyleSheet("color: green; font-weight: bold;")
                signup_error_lbl.setText("Sign Up successful!")
                print(f"Welcome! Email: {response.get('email')}")
            else:
                signup_error_lbl.setStyleSheet("color: red; font-weight: bold;")
                signup_error_lbl.setText(response.get("message"))
                
        except Exception as e:
            signup_error_lbl.setStyleSheet("color: red; font-weight: bold;")
            signup_error_lbl.setText(f"Connection error: {str(e)}")

        print("Sent a request to the server")
    else:
        signup_error_lbl.setStyleSheet("color: red; font-weight: bold;")
        signup_error_lbl.setText("Please fill all the fields.")


signup_logbtn = QPushButton("Sign up")
signup_logbtn.clicked.connect(signup)

signup_layout.addWidget(signup_logbtn)

signup_form_frame.setLayout(signup_layout)
signup_layout_1.addWidget(signup_form_frame)
signup_tab.setLayout(signup_layout_1)

tabs.addTab(signup_tab, "Sign Up")

main_layout = QVBoxLayout()
main_layout.addWidget(tabs)
main_layout.setContentsMargins(50, 30, 50, 30)
window.setLayout(main_layout)

window.show()
sys.exit(app.exec_())