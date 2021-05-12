from flask import Flask, url_for, request, redirect
from flask import render_template as render
from flask_mysqldb import MySQL
import yaml
import json
import MySQLdb


import decimal

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal): 
            return str(obj)

# Setting up the flask instance
app = Flask(__name__)

# Configure the database
db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)

link = {x:x for x in ["location", "product", "movement"]}
link["index"] = '/'

def init_database():
    cursor = mysql.connection.cursor()

    # Initialise all tables
    cursor.execute(""" 
    CREATE TABLE IF NOT EXISTS products(prod_id integer primary key auto_increment,
              prod_name varchar(20) UNIQUE NOT NULL,
              prod_quantity integer not null,
              unallocated_quantity integer);
    """)
    # Might have to create a trigger, let's see!

    cursor.execute(""" 
    CREATE TABLE IF NOT EXISTS location(loc_id integer primary key auto_increment,
										loc_name varchar(20) unique not null);
    """)
    cursor.execute(""" 
    CREATE TABLE IF NOT EXISTS logistics(trans_id integer primary key auto_increment,
										prod_id INTEGER NOT NULL,
										from_loc_id INTEGER NULL,
										to_loc_id INTEGER NULL,
										prod_quantity INTEGER NOT NULL,
										trans_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
										FOREIGN KEY(prod_id) REFERENCES products(prod_id),
										FOREIGN KEY(from_loc_id) REFERENCES location(loc_id),
										FOREIGN KEY(to_loc_id) REFERENCES location(loc_id));
    """)

    mysql.connection.commit()
    cursor.close()

@app.route('/')
def summary():
    init_database()
    msg = None
    q_data, warehouse, products = None, None, None
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("Select * from location")
        warehouse = cursor.fetchall()
        cursor.execute("Select * from products")
        products = cursor.fetchall()
        cursor.execute("""
        SELECT prod_name, unallocated_quantity, prod_quantity FROM products
        """)
        q_data = cursor.fetchall()

    except(MySQLdb.Error(not Warning), MySQLdb.Warning()) as e:
        msg = f"An error occured: {e}"
        print(msg)
    cursor.close()

    return render('index.html',link=link, title = "Summary", warehouses = warehouse, products = products, database = q_data)


@app.route('/location.html', methods=['POST', 'GET'])
def location():
    init_database()
    msg=None
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM location ORDER BY loc_id")
    warehouse_data = cursor.fetchall()


    cursor.execute("SELECT loc_name FROM location")
    loc_names = cursor.fetchall()
    loc_new = []
    for i in range(len(loc_names)):
        loc_new.append(loc_names[i][0])

    if request.method == 'POST':
        warehouse_name = request.form['warehouse_name']
        warehouse_name = warehouse_name.capitalize()

        transaction_allowed = False
        if warehouse_name not in ['', ' ', None] and warehouse_name not in loc_new:
            transaction_allowed=True
        
        if transaction_allowed:
            try:
                cursor.execute("INSERT INTO location(loc_name) VALUES(%s)", (warehouse_name,))
                mysql.connection.commit()

            except(MySQLdb.Error(not Warning), MySQLdb.Warning()) as e:
                msg = f"An error occured: {e}"

            else:
                msg = f"{warehouse_name} added succcessfully"

            if msg:
                print(msg)
            cursor.close()

            return redirect(url_for('location'))

    return render('location.html', link=link, warehouses=warehouse_data, transaction_message=msg, title = "Warehouse Locations")

@app.route('/product.html', methods=['POST', 'GET'])
def product():
    init_database()
    msg=None
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * from products")
    products = cursor.fetchall()

    cursor.execute("SELECT prod_name FROM products")
    prod_names = cursor.fetchall()
    prod_new = []
    for i in range(len(prod_names)):
        prod_new.append(prod_names[i][0])

    if request.method == 'POST':
        prod_name = request.form['prod_name']
        quantity = request.form['prod_quantity']
        prod_name = prod_name.capitalize()

        transaction_allowed = False
        if prod_name not in ['', ' ', None] and prod_name not in prod_new:
            if quantity not in ['', ' ', None]:
                transaction_allowed= True
            
        if transaction_allowed:
            try:
                cursor.execute("INSERT INTO products(prod_name, prod_quantity, unallocated_quantity) VALUES (%s, %s, %s)", (prod_name, quantity, quantity))
                mysql.connection.commit()

            except(MySQLdb.Error(not Warning), MySQLdb.Warning()) as e:
                msg = f"An error occured: {e}"

            else:
                msg = f"{prod_name} added succcessfully"

            if msg:
                print(msg)
            cursor.close()

            return redirect(url_for('product'))

    return render('product.html', link=link, products = products, transaction_message=msg, title="Products Log")

@app.route('/movement.html', methods=['POST', 'GET'])
def movement():
    init_database()
    msg=None
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM logistics")
    logistics_data = cursor.fetchall()

    cursor.execute("SELECT prod_id, prod_name, unallocated_quantity FROM products")
    products = cursor.fetchall()

    cursor.execute("SELECT loc_id, loc_name FROM location")
    locations = cursor.fetchall()

    
    # products - ((1, 'Piano', 250), (2, 'Iphone xr', 600), (6, 'Washing machine', 100), (7, 'Microwave', 50))
    # x in product - (1, 'Piano', 250)
    # x[0] = 1

    # for p_id in [x[0] for x in products]:
    #     print(p_id)
    
    # 1
    # 2
    # 6
    # 7
    # print(locations)
    # for l_id in [x[0] for x in locations]:
    #     print(l_id)

    # ((20, 'Andaman'), (19, 'Assam'), (26, 'Jodhpur'), (17, 'Puducherry'))
    # 20
    # 19
    # 26
    # 17
    log_summary = []
    for p_id in [x[0] for x in products]:
        cursor.execute("SELECT prod_name FROM products WHERE prod_id = %s", str(p_id,))
        temp_prod_name = cursor.fetchone() 
        #print(temp_prod_name)          ('Piano',)

        for l_id in [x[0] for x in locations]:
            cursor.execute("SELECT loc_name FROM location WHERE loc_id = %s", (l_id,)) #str(l_id,) giving an error
            temp_loc_name = cursor.fetchone()
            # print(temp_loc_name)       - (Andaman,)

            #e.g. prod_id = 1 = piano, loc_id = 1 = andaman
            cursor.execute("""                  
            SELECT SUM(log.prod_quantity)     
            FROM logistics log
            WHERE log.prod_id = %s AND log.to_loc_id = %s
            """, (p_id, l_id))

            sum_to_loc = cursor.fetchone()     # No.of pianos that enter andaman

            cursor.execute("""
            SELECT SUM(log.prod_quantity)
            FROM logistics log
            WHERE log.prod_id = %s AND log.from_loc_id = %s
            """, (p_id, l_id))

            sum_from_loc = cursor.fetchone()   # No. of pianos that leave andaman
            # print(sum_from_loc)

            if sum_from_loc[0] is None:        #e.g. (None,)  --> (0,) --> No pianos leave andaman
                sum_from_loc = (0,)
            if sum_to_loc[0] is None:          #No pianos enter andaman
                sum_to_loc = (0,)

            #how much enters andaman - how much leaves andaman = how much remains (allocated) in andaman
            # log_summary += [(temp_prod_name + temp_loc_name + (sum_to_loc[0] - sum_from_loc[0],) )]        ORRRRRRRRRRR
            log_summary.append(temp_prod_name + temp_loc_name + (sum_to_loc[0] - sum_from_loc[0],))    # (Piano,) + (Andaman,), (0,) = ('Piano', 'Andaman', 0)

    #print(log_summary)

    # [('Piano', 'Andaman', 0), ('Piano', 'Assam', 0), ('Piano', 'Jodhpur', 0), ('Piano', 'Puducherry', 0), 
    # ('Iphone xr', 'Andaman', 0), ('Iphone xr', 'Assam', 0), ('Iphone xr', 'Jodhpur', 0), ('Iphone xr', 'Puducherry', 0), 
    # ('Washing machine', 'Andaman', 0), ('Washing machine', 'Assam', 0), ('Washing machine', 'Jodhpur', 0), ('Washing machine', 'Puducherry', 0), 
    # ('Microwave', 'Andaman', 0), ('Microwave', 'Assam', 0), ('Microwave', 'Jodhpur', 0), ('Microwave', 'Puducherry', 0)]

    alloc_json = {}
    for row in log_summary:
        try:
            if row[1] in alloc_json[row[0]].keys():       #Check if Andaman exists in Piano ka keys, Check if Assam, exists in Piano ka keys, etc.
                alloc_json[row[0]][row[1]] += row[2]       #If yes, the add the quantity to the previous quantity
            else:
                alloc_json[row[0]][row[1]] = row[2]        #If no, add it as a new quantity
        except (KeyError, TypeError):
            alloc_json[row[0]] = {}                         #Make the value of piano empty
            alloc_json[row[0]][row[1]] = row[2]             #Add Andaman with quantity as a new value in the dictionary
    #print(alloc_json)

    # {'Piano': {'Andaman': 0, 'Assam': 0, 'Jodhpur': 0, 'Puducherry': 0}, 
    # 'Iphone xr': {'Andaman': 0, 'Assam': 0, 'Jodhpur': 0, 'Puducherry': 0}, 
    # 'Washing machine': {'Andaman': 0, 'Assam': 0, 'Jodhpur': 0, 'Puducherry': 0}, 
    # 'Microwave': {'Andaman': 0, 'Assam': 0, 'Jodhpur': 0, 'Puducherry': 0}}

    alloc_json = json.dumps(alloc_json, cls = Encoder)

    # print(alloc_json)

    # {"Piano": {"Andaman": 0, "Assam": 0, "Jodhpur": 0, "Puducherry": 0}, 
    # "Iphone xr": {"Andaman": 0, "Assam": 0, "Jodhpur": 0, "Puducherry": 0}, 
    # "Washing machine": {"Andaman": 0, "Assam": 0, "Jodhpur": 0, "Puducherry": 0}, 
    # "Microwave": {"Andaman": 0, "Assam": 0, "Jodhpur": 0, "Puducherry": 0}}

    if  request.method == 'POST':
        # transaction times are stored in UTC
        prod_name = request.form['prod_name']
        from_loc = request.form['from_loc']
        to_loc = request.form['to_loc']
        quantity = request.form['quantity']

        # if no 'from loc' is given, that means the product is being shipped to a warehouse (init condition)
        if from_loc in [None, '', ' ']:
            try:
                cursor.execute("""
                    INSERT INTO logistics(prod_id, to_loc_id, prod_quantity)
                    SELECT products.prod_id, location.loc_id, %s
                    FROM products, location
                    WHERE products.prod_name = %s AND location.loc_name = %s
                """, (quantity, prod_name, to_loc))

                # IMPORTANT to maintain consistency

                cursor.execute("""
                UPDATE products
                SET unallocated_quantity = unallocated_quantity - %s
                WHERE prod_name = %s
                """, (quantity, prod_name))

                mysql.connection.commit()
            
            except (MySQLdb.Error, MySQLdb.Warning) as e:
                msg = f"An error occured: {e}"
            else:
                msg = "Transaction added successfully"

        elif to_loc in [None, '', ' ']:
            print("To Location wasn't specified, will be unallocated")

            try:
                cursor.execute(""" 
                    INSERT INTO logistics(prod_id, from_loc_id, prod_quantity)
                    SELECT products.prod_id, location.loc_id, %s
                    FROM products, location
                    WHERE products.prod_name = %s AND location.loc_name = %s
                """, (quantity, prod_name, from_loc))

                #Important to maintain consistency
                cursor.execute("""
                    UPDATE products 
                    SET unallocated_quantity = unallocated_quantity + %s
                    WHERE prod_name = %s
                """, (quantity, prod_name))

                mysql.connection.commit()

            except(MySQLdb.Error, MySQLdb.Warning) as e:
                msg=f"An error occurred: {e}"
            else:
                msg = "Transaction added successfully"

        # if 'from loc' and 'to_loc' given the product is being shipped between warehouses
        else:
            try:
                cursor.execute("SELECT loc_id FROM location WHERE loc_name = %s", (from_loc,))
                from_loc = ''.join([str(x[0]) for x in cursor.fetchall()])     
                # cursor.fetchall -> ((1,)),      x -> (1,)       x[0] -> 1   join converts 1 into a string

                cursor.execute("SELECT loc_id FROM location WHERE loc_name = %s", (to_loc,)) 
                to_loc = ''.join([str(x[0]) for x in cursor.fetchall() ])
                
                 
                cursor.execute("SELECT prod_id FROM products WHERE prod_name = %s", (prod_name,)) 
                prod_id = ''.join([str(x[0]) for x in cursor.fetchall() ])

                cursor.execute("""
                    INSERT INTO logistics(prod_id, from_loc_id, to_loc_id, prod_quantity)
                    VALUES(%s, %s, %s, %s)
                """, (prod_id, from_loc, to_loc, quantity))

                mysql.connection.commit()

            except(MySQLdb.Error, MySQLdb.Warning) as e:
                msg=f"An error occurred: {e}"
            else:
                msg = "Transaction added successfully"

        #Print a transaction message if exists!
        if msg:
            print(msg)

        cursor.close()
        return redirect(url_for('movement'))


    return render('movement.html', title = "Product Movement", link=link, trans_message=msg, products=products, locations=locations, allocated = alloc_json, logs = logistics_data, database = log_summary)



@app.route('/delete')
def delete():
    # Make sure that the queries are working properly....I'm having some doubts about the datatypes
    type_ = request.args.get('type')
    cursor = mysql.connection.cursor()

    if type_ == 'location':
        id_ = request.args.get('loc_id')

        cursor.execute("SELECT prod_id, SUM(prod_quantity) FROM logistics where to_loc_id = %s GROUP BY prod_id", (id_,))
        in_place = cursor.fetchall()

        cursor.execute("SELECT prod_id, SUM(prod_quantity) FROM logistics where from_loc_id = %s GROUP BY prod_id", (id_,))
        out_place = cursor.fetchall()

        #Convert list of tuples to dict

        in_place = dict(in_place)
        out_place = dict(out_place)

        all_place = {}
        #Inplace = {1:20, 3:2000} - keys - prod_id  - toloc = mumbai
		#out_place = {3:100}  - keys - prod_id  - fromloc = mumbai

        for x in in_place.keys():     #calculator entered mumbai
            if x in out_place.keys():   #calculator left mumbai
                all_place[x] = in_place[x] - out_place[x]  #2000 fridges came to mumbai from kolkata, 100 fridges were sent to daman diu, therefore, 1900 remains in mumbai which will be unallocated if mumbai is deleted
            else:
                all_place[x] = in_place[x]

        for products_ in all_place.keys():
            cursor.execute("""
                UPDATE products SET unallocated_quantity = unallocated_quantity + %s WHERE prod_id = %s
            """, (all_place[products_], products_))

        cursor.execute("DELETE FROM location where loc_id = %s", (id_,))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('location'))

    elif type_ == 'product':
        id_ = request.args.get('prod_id')
        cursor.execute("DELETE FROM products WHERE prod_id = %s", (id_,))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('product'))


@app.route('/edit', methods=['POST', 'GET'])
def edit():
 
    # Try capitalize()

    type_ = request.args.get('type')
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT loc_name FROM location")
    loc_names = cursor.fetchall()
    loc_new = []
    for i in range(len(loc_names)):
        loc_new.append(loc_names[i][0])

    cursor.execute("SELECT prod_name FROM products")
    prod_names = cursor.fetchall()
    prod_new = []
    for i in range(len(prod_names)):
        prod_new.append(prod_names[i][0])
    

    if type_ == 'location' and request.method == 'POST':
        loc_id = request.form['loc_id']
        loc_name = request.form['loc_name']
        loc_name = loc_name.capitalize()

        if loc_name not in ['', ' ', None] and loc_name not in loc_new:
            cursor.execute("UPDATE location SET loc_name = %s WHERE loc_id = %s", (loc_name, loc_id))
            mysql.connection.commit()

        cursor.close()
        return redirect(url_for('location'))

    elif type_ == 'product' and request.method == 'POST':
        prod_id = request.form['product_id']
        prod_name = request.form['prod_name']
        prod_quantity = request.form['prod_quantity']
        prod_name = prod_name.capitalize()

        if prod_name not in ['', ' ', None] and prod_name not in prod_new:
            cursor.execute("UPDATE products SET prod_name = %s WHERE prod_id = %s", (prod_name, str(prod_id)))
	

        if prod_quantity not in ['', ' ', None] and prod_name not in prod_new:
            cursor.execute("SELECT prod_quantity FROM products WHERE prod_id = %s", (prod_id,))
            old_prod_quantity = cursor.fetchone()[0]
            cursor.execute("""
                UPDATE products SET prod_quantity = %s, unallocated_quantity = unallocated_quantity + %s - %s 
                WHERE prod_id = %s

            """, (prod_quantity, prod_quantity, old_prod_quantity, str(prod_id)))

        mysql.connection.commit()

        cursor.close()
        return redirect(url_for('product'))

    return render(url_for(type_))


if __name__ == '__main__':
	app.run(debug=True)