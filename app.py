from flask import Flask, render_template, request, redirect, url_for, flash
from web3 import Web3
from web3.middleware import geth_poa_middleware
from contract_info import abi, contract_address

app = Flask(__name__)
app.secret_key = 'key'

w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)
estate_agency_contract = w3.eth.contract(address=contract_address, abi=abi)

def authenticate_user(public_key_input, pass_key):
    try:
        unlocked = w3.geth.personal.unlock_account(public_key_input, pass_key)
        if unlocked:
            return True, public_key_input
        else:
            return False, "Не удалось разблокировать аккаунт."
    except Exception as authenticate_error:
        if 'already unlocked' in str(authenticate_error).lower():
            return True, public_key_input
        else:
            return False, f"Произошла ошибка во время авторизации: {authenticate_error}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    public_key = request.form['public_key']
    password = request.form['password']
    success, message = authenticate_user(public_key, password)
    if success:
        flash("Успешно вошли в систему.")
        return redirect(url_for('dashboard', account=public_key))
    else:
        flash(message)
        return redirect(url_for('index'))

@app.route('/header/<account>')
def dashboard(account):
    return render_template('header.html', account=account)

def ensure_account_unlocked(account):
    pass_key = request.form['key']
    try:
        unlocked = w3.geth.personal.unlock_account(account, pass_key)
        if unlocked:
            print("Аккаунт успешно разблокирован.")
        else:
            print("Не удалось разблокировать аккаунт.")
    except Exception as e:
        if 'already unlocked' in str(e).lower():
            print("Аккаунт уже разблокирован.")
        else:
            raise e
        
@app.route('/add_property/<account>', methods=['GET', 'POST'])
def add_property(account):
    # Получаем список всех объектов недвижимости
    ads = estate_agency_contract.functions.getEstates().call()
    
    if request.method == 'POST':
        # Получаем pass_key до его использования
        pass_key = request.form['key']
        
        # Разблокировка аккаунта до выполнения any операций
        try:
            unlocked = w3.geth.personal.unlock_account(account, pass_key)
            if unlocked:
                prop_size = int(request.form['prop_size'])
                prop_photo_url = request.form['prop_photo_url']
                prop_rooms = int(request.form['prop_rooms'])
                prop_type = int(request.form['prop_type']) - 1
                estate_agency_contract.functions.createEstate(prop_size, prop_photo_url, prop_rooms, prop_type).transact({
                    "from": account
                })
                flash("Объект недвижимости был успешно добавлен.")
            else:
                flash("Не удалось разблокировать аккаунт.")
        except Exception as e:
            flash(f"Произошла ошибка: {e}")
        
        return redirect(url_for('dashboard', account=account))
    
    return render_template('add_property.html', account=account, ads=ads)

@app.route('/unlock/<account>', methods=['GET', 'POST'])
def unlock(account):
    if request.method == 'POST':
        ensure_account_unlocked(account)
        flash("Аккаунт успешно разблокирован.")
        return redirect(url_for('add_property', account=account))
    return render_template('unlock.html', account=account)


@app.route('/transaction/<account>', methods=['GET', 'POST'])
def transaction(account):
    if request.method == 'POST':
        sender_account = account
        receiver_account = request.form['receiver_account']
        amount_in_ether = float(request.form['amount'])
        amount_in_wei = w3.to_wei(amount_in_ether, 'ether')
        
        try:
            tx_hash = w3.eth.send_transaction({
                'from': sender_account,
                'to': receiver_account,
                'value': amount_in_wei
            })
            flash(f"Перевод выполнен успешно. Хэш транзакции: {tx_hash.hex()}")
        except Exception as e:
            flash(f"Произошла ошибка при переводе средств: {e}")
        return redirect(url_for('dashboard', account=account))
    return render_template('transaction.html', account=account)

@app.route('/add_advertisement/<account>', methods=['GET', 'POST'])
def add_advertisement(account):
    ads = estate_agency_contract.functions.getAds().call()
    if request.method == 'POST':
        estate_id = int(request.form['estate_id'])
        ad_price_in_ether = float(request.form['ad_price'])
        ad_price_in_wei = w3.to_wei(ad_price_in_ether, 'ether')
        
        try:
            estate_agency_contract.functions.createAd(estate_id, ad_price_in_wei).transact({
                "from": account
            })
            flash("Объявление о продаже создано.")
        except Exception as e:
            flash(f"Произошла ошибка: {e}")
        return redirect(url_for('dashboard', account=account))
    return render_template('add_advertisement.html', account=account, ads=ads)

@app.route('/add_balance/<account>', methods=['GET', 'POST'])
def add_balance(account):
    if request.method == 'POST':
        sum_in_ether = float(request.form['sum'])
        sum_in_wei = w3.to_wei(sum_in_ether, 'ether')
        
        try:
            tx_hash = estate_agency_contract.functions.addFunds().transact({
                'from': account,
                'value': sum_in_wei
            })
            flash(f"Ваш баланс пополнен. Хэш транзакции: {tx_hash.hex()}")
        except Exception as e:
            flash(f"Произошла ошибка: {e}")
        return redirect(url_for('dashboard', account=account))
    return render_template('add_balance.html', account=account)

@app.route('/extract_funds/<account>', methods=['GET', 'POST'])
def extract_funds(account):
    if request.method == 'POST':
        withdraw_amount_in_ether = float(request.form['withdraw_amount'])
        withdraw_amount_in_wei = w3.to_wei(withdraw_amount_in_ether, 'ether')
        
        try:
            withdraw_tx = estate_agency_contract.functions.withdraw().transact({
                "from": account,
                "value": withdraw_amount_in_wei
            })
            flash(f"Средства успешно выведены. Хэш транзакции: {withdraw_tx.hex()}")
        except Exception as e:
            flash(f"Произошла ошибка при выводе средств: {e}")
        return redirect(url_for('dashboard', account=account))
    return render_template('extract_funds.html', account=account)

@app.route('/alter_property_status/<account>', methods=['GET', 'POST'])
def alter_property_status(account):
    if request.method == 'POST':
        property_id = int(request.form['property_id'])
        new_status = request.form['new_status'].lower() == "active"
        
        try:
            estate_agency_contract.functions.updateEstateStatus(property_id, new_status).transact({
                "from": account
            })
            flash(f"Статус недвижимости обновлён.")
        except Exception as e:
            flash(f"Произошла ошибка: {e}")
        return redirect(url_for('dashboard', account=account))
    return render_template('alter_property_status.html', account=account)

@app.route('/alter_ad_status/<account>', methods=['GET', 'POST'])
def alter_ad_status(account):
    if request.method == 'POST':
        ad_id = int(request.form['ad_id'])
        new_status = int(request.form['new_status'])
        
        try:
            estate_agency_contract.functions.updateAdStatus(ad_id, new_status).transact({
                "from": account
            })
            flash(f"Статус объявления обновлён.")
        except Exception as e:
            flash(f"Произошла ошибка: {e}")
        return redirect(url_for('dashboard', account=account))
    return render_template('alter_ad_status.html', account=account)

@app.route('/buy_property/<account>', methods=['GET', 'POST'])
def buy_property(account):
    ads = estate_agency_contract.functions.getAds().call()
    if request.method == 'POST':
        try:
            ad_id = int(request.form['ad_id'])  
            ad_price = ads[ad_id][2]
            balance = estate_agency_contract.functions.getBalance().call({
                "from": account
            })
            if balance >= ad_price:
                estate_agency_contract.functions.buyEstate(ad_id).transact({
                    "from": account,
                    "value": ad_price
                })
                flash("Недвижимость успешно куплена.")
        except ValueError:
            flash("Неверный ad_id. Пожалуйста, введите корректное значение.")
        except Exception as e:
            flash(f"Произошла ошибка: {e}")
        return redirect(url_for('dashboard', account=account))
    
    return render_template('buy_property.html', account=account, ads=ads)

@app.route('/show_account_balance/<account>')
def show_account_balance(account):
    try:
        balance = estate_agency_contract.functions.getBalance().call({
            "from": account
        })
        balance_in_ether = w3.from_wei(balance, 'ether')
        flash(f"Текущий баланс: {balance_in_ether} эфир")
    except Exception as e:
        flash(f"Произошла ошибка при получении баланса: {e}")
    return redirect(url_for('dashboard', account=account))


if __name__ == '__main__':
    app.run(debug=True)