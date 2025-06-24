from flask import Flask, render_template_string, request, send_file
from fpdf import FPDF
import io
import os
from datetime import datetime, timedelta
import unicodedata


ARTICLES_FILE = "articles.txt"

def load_articles_existants():
    if not os.path.exists(ARTICLES_FILE):
        return []
    with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
        return sorted(set([line.strip() for line in f if line.strip()]))

def save_new_articles(nouveaux_articles):
    existants = set(load_articles_existants())
    updated = existants.union(set(nouveaux_articles))
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        for article in sorted(updated):
            f.write(f"{article}\n")

app = Flask(__name__)

FACTURE_NUM_FILE = "numero_facture.txt"

def get_next_invoice_number():
    if not os.path.exists(FACTURE_NUM_FILE):
        with open(FACTURE_NUM_FILE, 'w') as f:
            f.write("2025-0000")
    with open(FACTURE_NUM_FILE, 'r+') as f:
        last_num = f.read().strip()
        prefix, number = last_num.split('-')
        next_num = int(number) + 1
        new_invoice = f"{prefix}-{next_num:04d}"
        f.seek(0)
        f.write(new_invoice)
        f.truncate()
    return new_invoice

def sanitize_text(text):
    return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')
def delete_article(article):
    articles = load_articles_existants()
    articles = [a for a in articles if a != article]
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        for a in sorted(articles):
            f.write(f"{a}\n")
HTML_TEMPLATE = """
<!doctype html>
<html lang=\"fr\">
<head>
  <meta charset=\"utf-8\">
  <title>Générateur de Factures</title>
  <style>
    body { font-family: Arial; margin: 2em; }
    label { display: block; margin-top: 1em; }
    table, th, td { border: 1px solid black; border-collapse: collapse; padding: 5px; }
    th { background-color: #007BFF; color: white; }
    .article-table { margin-top: 1em; }
    .facture-box { border: 2px solid black; display: inline-block; padding: 5px; font-size: 24px; font-weight: bold; color: #007BFF; }
    .section-title { color: #007BFF; font-weight: bold; }
    .remove-btn { color: red; cursor: pointer; font-weight: bold; }
    body {
      font-family: 'Segoe UI', sans-serif;
      margin: 0;
      padding: 1em;
      background: #f4f7fa;
      color: #333;
    }

    
    .container {
      max-width: 800px;
      margin: 0 auto;
      background-color: #f9fbfd;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }

    h1 {
      text-align: center;
      color: #2b7de9;
      font-size: 2em;
    }

    .facture-box {
      display: inline-block;
      font-weight: bold;
      font-size: 1.5em;
      color: #fff;
      background: #2b7de9;
      padding: 0.5em 1em;
      border-radius: 6px;
    }

    label {
      display: block;
      margin: 1em 0 0.5em;
      font-weight: 600;
    }

    textarea,
    input[type="text"],
    input[type="number"],
    select {
      width: 100%;
      padding: 0.6em;
      font-size: 1em;
      border: 1px solid #ccc;
      border-radius: 6px;
      box-sizing: border-box;
    }

    button {
      background-color: #00ee07;
      color: white;
      padding: 0.7em 1.5em;
      border: none;
      border-radius: 6px;
      font-size: 1em;
      margin-top: 1em;
      cursor: pointer;
      transition: background 0.3s ease;
    }

    button:hover {
      background-color: #1a5ec8;
    }

    .article-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1.5em;
    }

    .article-table th,
    .article-table td {
      border: 1px solid #ddd;
      padding: 0.75em;
      text-align: center;
    }

    .article-table th {
      background-color: #2b7de9;
      color: white;
    }

    .remove-btn {
      color: red;
      font-weight: bold;
      cursor: pointer;
    }

    @media (max-width: 768px) {
      .article-table th,
      .article-table td {
        font-size: 0.9em;
        padding: 0.5em;
      }

      .facture-box {
        font-size: 1.2em;
      }

      input, textarea, select {
        font-size: 0.95em;
      }
    }
    .center-btn {
      display: block;
      margin: 1em auto;
      text-align: center;
      padding: 0.7em 1.5em;
      background-color: #00ee07;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 1em;
      cursor: pointer;
      transition: background 0.3s ease;
    }

    .center-btn:hover {
      background-color: #1a5ec8;
    }
  </style>
  <script>
    function addArticleRow() {
      const table = document.getElementById("articles");
      const row = table.insertRow();
      const index = table.rows.length - 1;
      row.innerHTML = `
        <td>${index}</td>
        <td>
          <input list="designations" name="designation[]" placeholder="Choisir ou ajouter un article" required>
        </td>
        <td><input name='quantite[]' type='number' value='1' min='1' required></td>
        <td><input name='prix[]' type='number' step='0.01' value='0.00' required></td>
        <td><span class='remove-btn' onclick='removeRow(this)'>×</span></td>
      `;
    }
    function removeRow(btn) {
      const row = btn.parentNode.parentNode;
      row.parentNode.removeChild(row);
      updateIndexes();
    }
    function updateIndexes() {
      const rows = document.querySelectorAll("#articles tr");
      for (let i = 1; i < rows.length; i++) {
        rows[i].cells[0].innerText = i;
      }
    }
  </script>
</head>
<body>
  <div class="container">
    <h1><span class="facture-box">FACTURE</span></h1>

<form method="post">
  <label>Nom et adresse du client :<br>
    <textarea name="client_full" rows="4" cols="50" placeholder="Nom Prénom\nAdresse\nCode postal, Ville\nPays" required></textarea>
  </label>

  <table id="articles" class="article-table">
    <tr>
      <th>#</th><th>Désignation</th><th>Quantité</th><th>Prix Unitaire</th><th></th>
    </tr>
    <tr>
      <td>1</td>
      <td>
        <input list="designations" name="designation[]" placeholder="Choisir ou ajouter un article" required>
      </td>
      <td><input name='quantite[]' type='number' value='1' min='1' required></td>
      <td><input name='prix[]' type='number' step='0.01' value='0.00' required></td>
      <td></td>
    </tr>
  </table>
  <button type="button" onclick="addArticleRow()" class="center-btn">+ Ajouter un article</button>

  <label>Remise générale (en EUR, facultatif) :
    <input type='number' name='remise' step='0.01' value='0.00'>
  </label>

  <br><button type="submit" class="center-btn">📄 Générer la facture</button>
</form>

<hr>

<!-- Formulaire 2 : Ajout d’un article -->
<form method="post">
  <h3>Ajouter un nouvel article aux favoris</h3>
  <label>Nom du nouvel article :
    <input type="text" name="nouvel_article" placeholder="Ex: labubu gold" required>
  </label>
  <button type="submit" name="ajout_article" value="1" class="center-btn">Ajouter aux articles enregistrés</button>
</form>
<!-- Formulaire 3 : Suppression d’un article -->
<form method="post">
  <h3>Supprimer un article enregistré</h3>
  <label>Choisir l'article à supprimer :
    <select name="article_a_supprimer" required>
      {% for item in articles_existants %}
        <option value="{{ item }}">{{ item }}</option>
      {% endfor %}
    </select>
  </label>
  <button type="submit" name="supprimer_article" value="1" class="center-btn">Supprimer</button>
</form>
  <datalist id="designations">
    {{ARTICLE_OPTIONS}}
  </datalist>
    </div>

</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def invoice():
    if request.method == 'POST':
        # ➤ Cas 1 : Ajout d'article seulement
        if 'ajout_article' in request.form:
            article = sanitize_text(request.form.get('nouvel_article', '')).strip()
            if article:
                save_new_articles([article])

            # ➤ ON DOIT RENDRE LE FORMULAIRE APRÈS L'AJOUT
            options_html = '\n'.join([f"<option value=\"{a}\">" for a in load_articles_existants()])
            return render_template_string(HTML_TEMPLATE.replace("{{ARTICLE_OPTIONS}}", options_html), articles_existants=load_articles_existants())
        elif 'supprimer_article' in request.form:
            article = sanitize_text(request.form.get('article_a_supprimer', '')).strip()
            if article:
                delete_article(article)
            options_html = '\n'.join([f"<option value=\"{a}\">" for a in load_articles_existants()])
            return render_template_string(HTML_TEMPLATE.replace("{{ARTICLE_OPTIONS}}", options_html), articles_existants=load_articles_existants())
        else:
            client_full = sanitize_text(request.form['client_full'])
            designations = list(map(sanitize_text, request.form.getlist('designation[]')))
            save_new_articles(designations)
            quantites = list(map(int, request.form.getlist('quantite[]')))
            prix_unitaires = list(map(float, request.form.getlist('prix[]')))
            remise = float(request.form.get('remise', 0.0))

            invoice_number = get_next_invoice_number()
            today = datetime.today()
            due_date = today + timedelta(days=30)

            pdf = FPDF()
            pdf.add_page()

            pdf.set_font("Arial", 'B', 20)
            pdf.set_text_color(0, 102, 204)
            pdf.cell(0, 10, "FACTURE", ln=True)

            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, f"N° {invoice_number}", ln=True)

            vendeur_infos = [
                ["Saychi El", 'B'],
                ["Cécile Jiang", ''],
                ["cecilejiang12@gmail.com", ''],
                ["10 Rue Paulin Talabot", ''],
                ["93400 Saint-Ouen-sur-Seine France", ''],
                ["N° SIRET : 93803642300011", '']
            ]

            client_lines = client_full.strip().split('\n')
            pdf.set_font("Arial", '', 11)
            for i in range(max(len(vendeur_infos), len(client_lines))):
                pdf.set_x(10)
                if i < len(vendeur_infos):
                    font_style = vendeur_infos[i][1]
                    pdf.set_font("Arial", font_style, 11)
                    pdf.cell(95, 6, vendeur_infos[i][0], 0, 0)
                else:
                    pdf.cell(95, 6, "", 0, 0)
                pdf.set_x(110)
                if i == 0:
                    pdf.set_font("Arial", 'B', 11)
                else:
                    pdf.set_font("Arial", '', 11)
                if i < len(client_lines):
                    pdf.cell(95, 6, client_lines[i], 0, 1)
                else:
                    pdf.cell(95, 6, "", 0, 1)

            pdf.ln(4)
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 5, f"Date d'émission : {today.strftime('%d/%m/%Y')}", ln=True)
            pdf.cell(0, 5, f"Date exigibilite du paiement : {due_date.strftime('%d/%m/%Y')}", ln=True)
            pdf.ln(5)

            pdf.set_font("Arial", 'B', 11)
            pdf.set_fill_color(0, 102, 204)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(10, 8, "#", 1, 0, 'C', True)
            pdf.cell(80, 8, "Désignation", 1, 0, 'C', True)
            pdf.cell(30, 8, "Quantité", 1, 0, 'C', True)
            pdf.cell(35, 8, "Prix unitaire", 1, 0, 'C', True)
            pdf.cell(35, 8, "Montant HT", 1, 1, 'C', True)

            pdf.set_text_color(0, 0, 0)
            total = 0
            for idx, (des, qte, prix) in enumerate(zip(designations, quantites, prix_unitaires), 1):
                montant = qte * prix
                total += montant

                x0 = pdf.get_x()
                y0 = pdf.get_y()

                # → Désignation multi-ligne
                x1 = x0 + 10
                pdf.set_xy(x1, y0)
                pdf.set_font("Arial", 'B', 11)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(80, 7, des, border='LTR')

                y1 = pdf.get_y()
                pdf.set_x(x1)
                pdf.set_font("Arial", '', 9)
                pdf.set_text_color(130, 130, 130)
                pdf.multi_cell(80, 5, "Livraison de bien", border='LRB')
                y2 = pdf.get_y()

                # Hauteur totale de la ligne
                h = y2 - y0

                # → Cellule du numéro (#)
                pdf.set_xy(x0, y0)
                pdf.set_font("Arial", '', 11)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(10, h, str(idx), border=1, align='C')

                # → Autres colonnes
                pdf.set_xy(x1 + 80, y0)
                pdf.cell(30, h, str(qte), border=1, align='C')
                pdf.cell(35, h, f"{prix:.2f} EUR", border=1, align='C')
                pdf.cell(35, h, f"{montant:.2f} EUR", border=1, align='C')

                # Ligne suivante
                pdf.set_y(y2)
            pdf.ln(3)
            pdf.set_fill_color(240, 240, 240)  # gris clair
            ligne_y = pdf.get_y()
                
            # Encadré gris pour 3 lignes
            pdf.rect(x=pdf.l_margin, y=ligne_y, w=190, h=8, style='F')
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(155, 8, "Total HT", 0)
            pdf.cell(35, 8, f"{total:.2f} EUR", 0, ln=True)

            if remise > 0:
                total_final = total - remise

                pdf.set_fill_color(240, 240, 240)  # gris clair
                ligne_y = pdf.get_y()
                
                # Encadré gris pour 3 lignes
                pdf.rect(x=pdf.l_margin, y=ligne_y, w=190, h=8 * 2, style='F')

                pdf.set_y(ligne_y)
                pdf.set_font("Arial", 'B', 11)


                pdf.cell(155, 8, "Remise générale", 0)
                pdf.cell(35, 8, f"{remise:.2f} EUR", 0, ln=True)

                pdf.cell(155, 8, "Total HT final", 0)
                pdf.cell(35, 8, f"{total_final:.2f} EUR", 0, ln=True)

            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, "TVA non applicable, art. 293 B du CGI", ln=True)

            pdf.ln(10)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 102, 204)
            pdf.cell(0, 10, "Conditions de paiement", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, "Délai de paiement :", ln=True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, "30 jours", ln=True)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, "Moyens de paiement :", ln=True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, "Via Vinted", ln=True)
            pdf.ln(5)


            pdf_output = io.BytesIO()
            pdf_bytes = pdf.output(dest='S').encode('latin1', 'ignore')
            pdf_output.write(pdf_bytes)
            pdf_output.seek(0)
            with open(FACTURE_NUM_FILE, 'r+') as f:
                last_num = f.read().strip()
                prefix, number = last_num.split('-')
                next_num = int(number) + 1
            client_lines = client_full.split('\n')
            nom_prenom = client_lines[0].replace('_r', '').strip().split()
            return send_file(pdf_output, as_attachment=True, download_name=f"facture_{next_num-1}_{nom_prenom[0]}_{nom_prenom[1]}.pdf", mimetype='application/pdf')
    
    options_html = '\n'.join([f"<option value=\"{a}\">" for a in load_articles_existants()])
    return render_template_string(HTML_TEMPLATE.replace("{{ARTICLE_OPTIONS}}", options_html), articles_existants=load_articles_existants())

if __name__ == "__main__":
    app.run(debug=True)