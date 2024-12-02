import streamlit as st
import json
import os
from rapidfuzz import fuzz
import hashlib
import csv
import pandas as pd

# File paths
PRODUCTS_FILE = "product_prices.json"
CATEGORIES_FILE = "categories.json"
DATABASE_FOLDER = "database"
USERS_FILE = os.path.join(DATABASE_FOLDER, "users.json")

os.makedirs(DATABASE_FOLDER, exist_ok=True)

def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}  # Return an empty dictionary if the file is invalid
    return {}  # Return an empty dictionary if the file doesn't exist

def save_data(data, file_path):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

def generate_csv(data, selected_columns, file_name="output.csv"):
    """Generate a CSV file with selected columns from the data."""
    if not data:
        return None

    file_path = os.path.join(DATABASE_FOLDER, file_name)
    with open(file_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        # Write the header
        writer.writerow(selected_columns)
        # Write the rows
        for product, details in data.items():
            row = [details.get(col, product if col == "Product Name" else "") for col in selected_columns]
            writer.writerow(row)
    return file_path

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    """Authenticate user credentials."""
    users = load_data(USERS_FILE)
    hashed_password = hash_password(password)
    user = users.get(username)
    if user and user["password"] == hashed_password:
        return user
    return None

def create_default_admin():
    """Create a default admin user if not exists."""
    users = load_data(USERS_FILE)
    if not isinstance(users, dict):  # Ensure users is a dictionary
        users = {}
    if "Admin" not in users:
        users["Admin"] = {"password": hash_password("1234"), "role": "Admin"}
        save_data(users, USERS_FILE)

def signup(username, password, role):
    """Sign up a new user."""
    users = load_data(USERS_FILE)
    if username in users:
        return False, "Username already exists!"
    users[username] = {"password": hash_password(password), "role": role}
    save_data(users, USERS_FILE)
    return True, "User created successfully!"

def format_username(username):
    if "@" in username:
        return username.split("@")[0]  # Strip the domain
    return username

def create_sidebar():
    formatted_username = format_username(st.session_state['username'])
    
    # Sidebar header with a greeting
    st.sidebar.markdown(f"""
        <div style="text-align: center; background-color: #1E1E1E; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="margin: 0;">Welcome, {formatted_username}!</h2>
        </div>
    """, unsafe_allow_html=True)

    # Logout button
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()

    # Navigation menu
    st.sidebar.markdown("<hr style='border: 1px solid #555;'>", unsafe_allow_html=True)

    if st.session_state.role == "Admin":
        menu_choice = st.sidebar.radio(
            "Navigation",
            ["Add New Product", "Update Product", "View All Products",
             "Manage Categories", "Generate CSV", "User Management"],
            key="menu_choice",
        )
    else:
        menu_choice = st.sidebar.radio(
            "Navigation",
            ["All Products", "CSV Generate"],
            key="menu_choice",
        )

    # Return the selected choice
    return menu_choice

def main():
    data = load_data(PRODUCTS_FILE)
    categories = load_data(CATEGORIES_FILE).get("categories", [])
    # Ensure default admin exists
    create_default_admin()

    # Session state for authentication
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.role = None

    # Authentication flow
    if not st.session_state.authenticated:
        st.title("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            user = authenticate_user(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = user["role"]
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
    else:
        st.title("Product Price Management System")
        main_menu_choice = create_sidebar()  # Get the selected menu choice from sidebar

        if main_menu_choice == "Query Product Price":
            st.header("Query")
            query_input = st.text_input("Enter Product or Category").strip()

            if st.button("Search"):
                if not data:
                    st.warning("No products found. Please add some products first.")
                else:
                    # Check if input matches a category
                    category_matches = {
                        name: details
                        for name, details in data.items()
                        if details["category"].lower() == query_input.lower()
                    }

                    if category_matches:
                        query_input = query_input.upper()
                        st.write(f"{query_input}:")
                        for name, details in category_matches.items():
                            st.write(
                                f"{name}: {details['purchase_price']}/{details['selling_price']}"
                            )
                    else:
                        # Check for product name similarity
                        matches = []
                        for product_name in data.keys():
                            similarity_score = fuzz.token_set_ratio(query_input, product_name)
                            if similarity_score >= 50:  # Threshold for similarity
                                matches.append((product_name, similarity_score))

                        if matches:
                            matches.sort(key=lambda x: x[1], reverse=True)
                            best_match, score = matches[0]
                            product = data[best_match]
                            score = int(score)
                            st.write(
                                f"{best_match}({score}%): {product['purchase_price']}/{product['selling_price']}"
                            )
                        else:
                            st.warning("No matching product or category found. Please check your input.")

        elif main_menu_choice == "User Management" and st.session_state.role == "Admin":
            st.header("User Management")
            st.write("Add new users here:")
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password", type="password")
            role = st.selectbox("Role", options=["Admin", "User"])
            if st.button("Create User"):
                success, message = signup(new_username, new_password, role)
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        elif main_menu_choice == "Generate CSV" and st.session_state.role == "Admin":
            st.header("Generate CSV File")
            
            # Select category filter
            selected_category = st.selectbox("Filter by Category", options=["All"] + categories)

            # Filter data by category
            if selected_category == "All":
                filtered_data = data
            else:
                filtered_data = {name: details for name, details in data.items() if details["category"] == selected_category}

            if filtered_data:
                # Select columns to include
                all_columns = ["Product Name"] + list(next(iter(data.values())).keys())
                selected_columns = st.multiselect("Select Columns to Include in CSV", options=all_columns, default=all_columns)

                if st.button("Generate CSV"):
                    if selected_columns:
                        file_path = generate_csv(filtered_data, selected_columns)
                        if file_path:
                            with open(file_path, "rb") as file:
                                st.download_button(
                                    label="Download CSV File",
                                    data=file,
                                    file_name="products.csv",
                                    mime="text/csv"
                                )
                            st.success("CSV file generated successfully!")
                        else:
                            st.error("Failed to generate CSV file.")
                    else:
                        st.error("Please select at least one column to include in the CSV.")
            else:
                st.info("No products available for the selected category.")

        elif main_menu_choice == "CSV Generate":
            st.header("Generate CSV File")
            
            # Select category filter
            selected_category = st.selectbox("Filter by Category", options=["All"] + categories)

            # Filter data by category
            if selected_category == "All":
                filtered_data = data
            else:
                filtered_data = {name: details for name, details in data.items() if details["category"] == selected_category}

            if filtered_data:
                # Select columns to include, excluding "purchase price"
                all_columns = ["Product Name"] + [
                    column for column in list(next(iter(data.values())).keys())
                    if column != "purchase_price"
                ]
                selected_columns = st.multiselect("Select Columns to Include in CSV", options=all_columns, default=all_columns)

                if st.button("Generate CSV"):
                    if selected_columns:
                        file_path = generate_csv(filtered_data, selected_columns)
                        if file_path:
                            with open(file_path, "rb") as file:
                                st.download_button(
                                    label="Download CSV File",
                                    data=file,
                                    file_name="products.csv",
                                    mime="text/csv"
                                )
                            st.success("CSV file generated successfully!")
                        else:
                            st.error("Failed to generate CSV file.")
                    else:
                        st.error("Please select at least one column to include in the CSV.")
            else:
                st.info("No products available for the selected category.")

        elif main_menu_choice == "Add New Product" and st.session_state.role == "Admin":
            st.header("Add a New Product")
            product_name = st.text_input("Product Name")
            category = st.selectbox("Category", options=["Select a Category"] + categories)
            purchase_price = st.number_input("Purchase Price", min_value=0, step=1)
            dealer_price = st.number_input("Dealer Price", min_value=0, step=1)
            selling_price = st.number_input("Selling Price", min_value=0, step=1)

            if st.button("Add Product"):
                if product_name and category != "Select a Category" and purchase_price > 0 and selling_price > 0 and dealer_price > 0:
                    data[product_name] = {
                        "category": category,
                        "purchase_price": purchase_price,
                        "dealer_price": dealer_price,
                        "selling_price": selling_price,
                    }
                    save_data(data, PRODUCTS_FILE)
                    st.success(f"Product '{product_name}' added successfully!")
                else:
                    st.error("Please enter valid details and select a category.")

        elif main_menu_choice == "Update Product" and st.session_state.role == "Admin":
            st.header("Edit Product")
            selected_category = st.selectbox("Select a Category", options=categories)

            if selected_category:
                products_in_category = {name: details for name, details in data.items() if details["category"] == selected_category}

                if products_in_category:
                    selected_product = st.selectbox("Select a Product to Edit", options=list(products_in_category.keys()))

                    if selected_product:
                        new_category = st.text_input("New Category", value=data[selected_product]["category"])
                        new_purchase_price = st.number_input("New Purchase Price", min_value=0, value=data[selected_product]["purchase_price"], step=1)
                        new_dealer_price = st.number_input("New dealer Price", min_value=0, value=data[selected_product]["dealer_price"], step=1)
                        new_selling_price = st.number_input("New Selling Price", min_value=0, value=data[selected_product]["selling_price"], step=1)

                        if st.button("Update Product"):
                            data[selected_product] = {
                                "category": new_category,
                                "purchase_price": new_purchase_price,
                                "dealer_price": new_dealer_price,
                                "selling_price": new_selling_price,
                            }
                            save_data(data, PRODUCTS_FILE)
                            st.success(f"Product '{selected_product}' has been updated!")
                else:
                    st.warning("No products found in the selected category.")

        elif main_menu_choice == "View All Products" and st.session_state.role == "Admin":
            st.header("All Products")
            selected_category = st.selectbox("Filter by Category", options=["All"] + categories)

            # Filter the data based on selected category
            if selected_category == "All":
                filtered_data = data
            else:
                filtered_data = {name: details for name, details in data.items() if details["category"] == selected_category}

            # Convert the filtered data into a DataFrame
            if filtered_data:
                product_list = []
                for product_name, details in filtered_data.items():
                    product_info = {
                        "Product Name": product_name,
                        "Category": details["category"],
                        "Purchase Price": details["purchase_price"],
                        "Dealer Price": details["dealer_price"],
                        "Selling Price": details["selling_price"]
                    }
                    product_list.append(product_info)

                df = pd.DataFrame(product_list)

                # Pagination Implementation
                page_size = 10  # Number of rows per page
                total_pages = len(df) // page_size + (1 if len(df) % page_size > 0 else 0)

                # If there's more than 1 page, show the slider; otherwise, skip it
                if total_pages > 1:
                    current_page = st.slider("Page", 1, total_pages, 1)
                else:
                    current_page = 1  # Only one page, set it to 1

                # Slice the DataFrame to get the rows for the current page
                start_idx = (current_page - 1) * page_size
                end_idx = start_idx + page_size
                page_df = df.iloc[start_idx:end_idx]

                # Display the paginated table
                st.dataframe(page_df)
            else:
                st.info("No products found for the selected category.")
        
        elif main_menu_choice == "All Products":
            st.header("All Products")
            selected_category = st.selectbox("Filter by Category", options=["All"] + categories)

            # Filter the data based on selected category
            if selected_category == "All":
                filtered_data = data
            else:
                filtered_data = {name: details for name, details in data.items() if details["category"] == selected_category}

            # Convert the filtered data into a DataFrame
            if filtered_data:
                product_list = []
                for product_name, details in filtered_data.items():
                    product_info = {
                        "Product Name": product_name,
                        "Category": details["category"],
                        "Dealer Price": details["dealer_price"],
                        "Selling Price": details["selling_price"]
                    }
                    product_list.append(product_info)

                df = pd.DataFrame(product_list)

                # Pagination Implementation
                page_size = 10  # Number of rows per page
                total_pages = len(df) // page_size + (1 if len(df) % page_size > 0 else 0)

                # If there's more than 1 page, show the slider; otherwise, skip it
                if total_pages > 1:
                    current_page = st.slider("Page", 1, total_pages, 1)
                else:
                    current_page = 1  # Only one page, set it to 1

                # Slice the DataFrame to get the rows for the current page
                start_idx = (current_page - 1) * page_size
                end_idx = start_idx + page_size
                page_df = df.iloc[start_idx:end_idx]

                # Display the paginated table
                st.dataframe(page_df)
            else:
                st.info("No products found for the selected category.")
        
        elif main_menu_choice == "Manage Categories" and st.session_state.role == "Admin":
            st.header("Manage Categories")
            new_category = st.text_input("New Category")
            if st.button("Add Category"):
                if new_category and new_category not in categories:
                    categories.append(new_category)
                    save_data({"categories": categories}, CATEGORIES_FILE)
                    st.success(f"Category '{new_category}' added successfully!")
                elif new_category in categories:
                    st.warning("Category already exists!")
                else:
                    st.error("Please enter a valid category name.")

            if categories:
                selected_category = st.selectbox("Select a Category to Delete", options=categories)
                if st.button("Delete Category"):
                    if selected_category in categories:
                        categories.remove(selected_category)
                        data = {k: v for k, v in data.items() if v["category"] != selected_category}
                        save_data(data, PRODUCTS_FILE)
                        save_data({"categories": categories}, CATEGORIES_FILE)
                        st.success(f"Category '{selected_category}' deleted successfully!")
                    else:
                        st.error("Selected category not found!")
            else:
                st.info("No categories available. Please add a category first.")

if __name__ == "__main__":
    main()
