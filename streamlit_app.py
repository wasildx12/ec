"""EcoCoin on Streamlit. Run locally:  streamlit run streamlit_app.py
Reuses the same database models and reward rules as the Flask version."""
from collections import defaultdict
import pandas as pd
import streamlit as st

from app import app as flask_app            # gives us the database + tables
from models import (db, User, WasteCategory, CollectionPoint, Submission, Transaction)
from services.rewards import approve_submission, reject_submission, calculate_coins, MAX_WEIGHT_G

st.set_page_config(page_title="EcoCoin", page_icon="♻️", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&family=DM+Sans:wght@400;500;700&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
h1,h2,h3{font-family:'Bricolage Grotesque',sans-serif!important;letter-spacing:-.02em;color:#0e2a1f}
.stApp{background:linear-gradient(160deg,#eaf4ec,#d8eedf 60%,#f6ecd3)}
.blob{position:fixed;border-radius:50%;filter:blur(60px);opacity:.65;z-index:0;pointer-events:none;animation:drift 18s ease-in-out infinite alternate}
.b1{width:420px;height:420px;background:#6fcf97;top:-100px;left:-80px}
.b2{width:380px;height:380px;background:#f2b84b;top:35%;right:-100px;animation-duration:22s}
@keyframes drift{to{transform:translate(70px,50px) scale(1.15)}}
/* acrylic header */
header[data-testid="stHeader"]{background:rgba(255,255,255,.38)!important;
  -webkit-backdrop-filter:blur(18px) saturate(170%);backdrop-filter:blur(18px) saturate(170%);
  border-bottom:1px solid rgba(255,255,255,.65);box-shadow:0 6px 24px rgba(14,42,31,.10)}
.brandbar{position:fixed;top:0;left:3.5rem;z-index:999991;height:3.75rem;display:flex;align-items:center;gap:.55rem;
  font:800 1.3rem 'Bricolage Grotesque',sans-serif;color:#0e2a1f}
.coin{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;font-size:.95rem;color:#0e2a1f;
  background:radial-gradient(circle at 30% 30%,#ffe29a,#f2b84b 55%,#c98a14)}
section[data-testid="stSidebar"]{background:rgba(255,255,255,.45);-webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px)}
.block-container{padding-top:5rem;max-width:1100px;position:relative;z-index:1}
/* hero */
.hero{display:flex;align-items:center;justify-content:space-between;gap:2rem;flex-wrap:wrap;margin:1rem 0 2rem}
.hero h1{font-size:clamp(2.2rem,5vw,3.8rem);font-weight:800;margin:0 0 .8rem;animation:rise .9s cubic-bezier(.2,.8,.2,1) both}
.hero p{font-size:1.1rem;color:#5b7165;max-width:30rem;animation:rise .9s .15s both}
@keyframes rise{from{opacity:0;transform:translateY(26px)}}
.loop{position:relative;width:260px;height:260px}
.ring{width:100%;height:100%;animation:spin 14s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.bigcoin{position:absolute;inset:27%;display:grid;place-items:center;border-radius:50%;font:800 2.8rem 'Bricolage Grotesque';color:#0e2a1f;
  background:radial-gradient(circle at 30% 30%,#ffe29a,#f2b84b 55%,#c98a14);animation:bob 3.5s ease-in-out infinite}
@keyframes bob{50%{transform:translateY(-10px) rotateY(180deg)}}
.leaf{position:absolute;width:20px;height:20px;background:#3fae6a;border-radius:0 100% 0 100%;opacity:.8;animation:float 7s ease-in-out infinite}
@keyframes float{50%{transform:translate(16px,-24px) rotate(80deg)}}
/* cards + buttons */
div[data-testid="stMetric"],div[data-testid="stForm"],.card{background:rgba(255,255,255,.72);border:1px solid rgba(255,255,255,.9);
  border-radius:18px;padding:1rem 1.2rem;box-shadow:0 10px 30px rgba(14,42,31,.12);animation:pop .6s cubic-bezier(.2,1.4,.4,1) both;transition:transform .25s}
div[data-testid="stMetric"]:hover{transform:translateY(-5px)}
@keyframes pop{from{opacity:0;transform:scale(.94) translateY(14px)}}
.stButton>button,.stFormSubmitButton>button{border-radius:999px;font-weight:700;border:0;background:#f2b84b;color:#0e2a1f;
  box-shadow:0 6px 16px rgba(201,138,20,.35);transition:transform .2s,box-shadow .2s}
.stButton>button:hover,.stFormSubmitButton>button:hover{transform:translateY(-2px);color:#0e2a1f;box-shadow:0 10px 22px rgba(201,138,20,.45)}
.balance{font:800 4rem 'Bricolage Grotesque';color:#c98a14;line-height:1}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
<div class="blob b1"></div><div class="blob b2"></div>
<div class="brandbar"><span class="coin">E</span>EcoCoin</div>
"""
st.markdown(CSS, unsafe_allow_html=True)

HERO = """
<div class="hero"><div><h1>Sort it. Weigh it.<br>Get paid in EcoCoins.</h1>
<p>Drop recyclables at a collection point, a collector verifies the weight, and coins land in your wallet right away.</p></div>
<div class="loop"><svg viewBox="0 0 200 200" class="ring">
<path d="M100 20 A80 80 0 0 1 169 140" fill="none" stroke="#f2b84b" stroke-width="10" stroke-linecap="round"/>
<path d="M169 140 A80 80 0 0 1 31 140" fill="none" stroke="#3fae6a" stroke-width="10" stroke-linecap="round"/>
<path d="M31 140 A80 80 0 0 1 100 20" fill="none" stroke="#7fd6a0" stroke-width="10" stroke-linecap="round"/></svg>
<div class="bigcoin">E</div><span class="leaf" style="top:4%;left:12%"></span><span class="leaf" style="bottom:10%;right:2%;background:#f2b84b;animation-delay:-3s"></span></div></div>
"""


@st.cache_resource
def ensure_demo_data():
    """On a fresh database (e.g. after a Streamlit Cloud restart) load the demo accounts."""
    with flask_app.app_context():
        if not User.query.first():
            import seed  # noqa: F401  (runs the seed script once)
    return True


def flash(msg, kind="success"):
    st.session_state["flash"] = (kind, msg)


def show_flash():
    if "flash" in st.session_state:
        kind, msg = st.session_state.pop("flash")
        (st.success if kind == "success" else st.error)(msg)


# ---------- auth ----------
def auth_page():
    st.markdown(HERO, unsafe_allow_html=True)
    login_tab, reg_tab = st.tabs(["Log in", "Create account"])
    with login_tab, st.form("login"):
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Log in"):
            u = User.query.filter_by(email=email.strip().lower()).first()
            if u and u.check_password(pw):
                st.session_state.uid = u.id
                st.rerun()
            st.error("Wrong email or password.")
    with reg_tab, st.form("register"):
        name = st.text_input("Name")
        email = st.text_input("Email ")
        pw = st.text_input("Password (6+ characters)", type="password")
        if st.form_submit_button("Create account"):
            email = email.strip().lower()
            if not name.strip() or "@" not in email or len(pw) < 6:
                st.error("Enter your name, a valid email and a password of 6+ characters.")
            elif User.query.filter_by(email=email).first():
                st.error("That email is already registered. Log in instead.")
            else:
                u = User(name=name.strip(), email=email, role="user")  # public sign-up is always 'user'
                u.set_password(pw)
                db.session.add(u)
                db.session.commit()
                st.session_state.uid = u.id
                st.rerun()
    with st.expander("Demo accounts"):
        st.code("admin@ecocoin.test / admin123\ncollector@ecocoin.test / collect123\nuser@ecocoin.test / user123")


# ---------- pages ----------
def stats_for(me):
    sq, tq = Submission.query, Transaction.query.filter(Transaction.amount > 0)
    if me.role == "user":
        sq, tq = sq.filter_by(user_id=me.id), tq.filter_by(user_id=me.id)
    subs, txs = sq.all(), tq.order_by(Transaction.created_at).all()
    by_day, by_cat = defaultdict(int), defaultdict(float)
    for t in txs:
        by_day[t.created_at.strftime("%d %b")] += t.amount
    for s in subs:
        if s.status == "approved":
            by_cat[s.category.name] += s.verified_weight_g / 1000
    status = {k: sum(1 for s in subs if s.status == k) for k in ("pending", "approved", "rejected")}
    return subs, txs, by_day, by_cat, status


def dashboard(me):
    st.title(f"Hi, {me.name}")
    st.caption("Your recycling at a glance" if me.role == "user" else "Platform-wide numbers")
    subs, txs, by_day, by_cat, status = stats_for(me)
    c = st.columns(4)
    c[0].metric("Wallet balance", me.balance)
    c[1].metric("Coins earned", sum(t.amount for t in txs))
    c[2].metric("Kg recycled", round(sum(by_cat.values()), 2))
    c[3].metric("Submissions", len(subs))
    a, b, d = st.columns(3)
    with a:
        st.subheader("Coins over time")
        if by_day: st.area_chart(pd.Series(by_day, name="coins"), color="#3fae6a")
        else: st.info("Earn your first coins to see this chart.")
    with b:
        st.subheader("Kg by category")
        if by_cat: st.bar_chart(pd.Series(by_cat, name="kg"), color="#f2b84b")
        else: st.info("No approved waste yet.")
    with d:
        st.subheader("Submissions by status")
        if subs: st.bar_chart(pd.Series(status, name="count"), color="#2f7d5b")
        else: st.info("Nothing submitted yet.")


def submit_page(me):
    st.title("Submit waste")
    cats = WasteCategory.query.filter_by(is_active=True).all()
    points = CollectionPoint.query.filter_by(is_active=True).all()
    if not cats or not points:
        st.warning("No active categories or collection points yet. Ask an admin to add some.")
        return
    cat = st.selectbox("Category", cats, format_func=lambda c: f"{c.name} ({c.coins_per_kg} coins/kg)")
    kg = st.number_input("Weight in kg", min_value=0.01, max_value=100.0, value=1.0, step=0.1)
    grams = int(round(kg * 1000))
    st.info(f"Estimated reward: **{calculate_coins(grams, cat.coins_per_kg)} coins** (final amount uses the collector's verified weight)")
    point = st.selectbox("Collection point", points, format_func=lambda p: f"{p.name}, {p.address}")
    note = st.text_input("Note (optional)", max_chars=200)
    if st.button("Send for verification"):
        if not 0 < grams <= MAX_WEIGHT_G:
            st.error("Weight must be above 0 and at most 100 kg.")
        else:
            db.session.add(Submission(user_id=me.id, category_id=cat.id, point_id=point.id,
                                      claimed_weight_g=grams, note=note.strip()))
            db.session.commit()
            flash("Submitted! A collector will verify it soon.")
            st.session_state.goto = "Wallet"   # applied before the menu is drawn on the next run
            st.rerun()


def wallet_page(me):
    st.title("Your wallet")
    st.markdown(f'<div class="card"><span>Balance</span><div class="balance">{me.balance}</div>EcoCoins</div>', unsafe_allow_html=True)
    txs = Transaction.query.filter_by(user_id=me.id).order_by(Transaction.created_at.desc()).all()
    st.subheader("Transaction history")
    if txs:
        st.dataframe(pd.DataFrame([{"Date": t.created_at.strftime("%d %b %Y %H:%M"), "Description": t.description,
                                    "Coins": f"+{t.amount}"} for t in txs]), hide_index=True, use_container_width=True)
    else:
        st.info("No coins yet. Submit your first waste to start earning.")
    st.subheader("My submissions")
    subs = Submission.query.filter_by(user_id=me.id).order_by(Submission.created_at.desc()).all()
    if subs:
        st.dataframe(pd.DataFrame([{"Date": s.created_at.strftime("%d %b %Y"), "Category": s.category.name,
                                    "Claimed kg": s.claimed_weight_g / 1000, "Status": s.status,
                                    "Reason": s.reject_reason or ""} for s in subs]), hide_index=True, use_container_width=True)


def review_page(me):
    st.title("Review queue")
    pending = Submission.query.filter_by(status="pending").order_by(Submission.created_at).all()
    if not pending:
        st.info("All caught up. No submissions are waiting.")
    for s in pending:
        with st.container(border=True):
            st.markdown(f"**{s.category.name}** from {s.user.name}")
            st.caption(f"Claimed {s.claimed_weight_g/1000:.2f} kg at {s.point.name} · {s.category.coins_per_kg} coins/kg"
                       + (f' · "{s.note}"' if s.note else ""))
            c1, c2, c3, c4 = st.columns([1.2, 1, 1.6, 1])
            kg = c1.number_input("Verified kg", 0.01, 100.0, max(s.claimed_weight_g / 1000, 0.01), 0.01, key=f"kg{s.id}")
            if c2.button("Approve", key=f"ok{s.id}"):
                try:
                    coins = approve_submission(s, me, int(round(kg * 1000)))
                    flash(f"Approved. {coins} EcoCoins credited to {s.user.name}.")
                except ValueError as e:
                    flash(str(e), "error")
                st.rerun()
            reason = c3.text_input("Reject reason", key=f"why{s.id}")
            if c4.button("Reject", key=f"no{s.id}"):
                try:
                    reject_submission(s, me, reason)
                    flash("Submission rejected.")
                except ValueError as e:
                    flash(str(e), "error")
                st.rerun()
    done = Submission.query.filter(Submission.status != "pending").order_by(Submission.reviewed_at.desc()).limit(10).all()
    if done:
        st.subheader("Recently reviewed")
        st.dataframe(pd.DataFrame([{"User": s.user.name, "Category": s.category.name,
                                    "Verified kg": (s.verified_weight_g or 0) / 1000, "Coins": s.coins_awarded,
                                    "Status": s.status} for s in done]), hide_index=True, use_container_width=True)


def admin_page(me):
    st.title("Admin")
    st.subheader("Collection points")
    for p in CollectionPoint.query.all():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{p.name}**, {p.address}")
        c2.write("active" if p.is_active else "inactive")
        if c3.button("Deactivate" if p.is_active else "Activate", key=f"pt{p.id}"):
            p.is_active = not p.is_active
            db.session.commit()
            st.rerun()
    with st.form("addpoint", clear_on_submit=True):
        n, a = st.text_input("Name"), st.text_input("Address")
        if st.form_submit_button("Add point"):
            if n.strip() and a.strip():
                db.session.add(CollectionPoint(name=n.strip(), address=a.strip()))
                db.session.commit()
                flash("Collection point added.")
                st.rerun()
            st.error("Name and address are required.")
    st.subheader("Waste categories and rates")
    for cat in WasteCategory.query.all():
        c1, c2, c3, c4 = st.columns([2, 1.2, 1, 1])
        c1.write(f"**{cat.name}**")
        rate = c2.number_input("Coins per kg", 0, 10000, cat.coins_per_kg, key=f"r{cat.id}", label_visibility="collapsed")
        act = c3.checkbox("Active", cat.is_active, key=f"a{cat.id}")
        if c4.button("Save", key=f"s{cat.id}"):
            cat.coins_per_kg, cat.is_active = int(rate), act
            db.session.commit()
            flash("Category updated.")
            st.rerun()
    with st.form("addcat", clear_on_submit=True):
        n, r = st.text_input("New category"), st.number_input("Coins per kg", 0, 10000, 10)
        if st.form_submit_button("Add category"):
            if n.strip() and not WasteCategory.query.filter_by(name=n.strip()).first():
                db.session.add(WasteCategory(name=n.strip(), coins_per_kg=int(r)))
                db.session.commit()
                flash("Category added.")
                st.rerun()
            st.error("Enter a unique category name.")


PAGES = {"Dashboard": dashboard, "Submit waste": submit_page, "Wallet": wallet_page,
         "Review queue": review_page, "Admin": admin_page}
ALLOWED = {"user": ["Dashboard", "Submit waste", "Wallet"],
           "collector": ["Dashboard", "Review queue"],
           "admin": ["Dashboard", "Review queue", "Admin"]}


def main():
    ensure_demo_data()
    me = db.session.get(User, st.session_state["uid"]) if "uid" in st.session_state else None
    if not me:
        auth_page()
        return
    allowed = ALLOWED[me.role]
    if "goto" in st.session_state:
        st.session_state.page = st.session_state.pop("goto")
    if st.session_state.get("page") not in allowed:
        st.session_state.page = allowed[0]
    with st.sidebar:
        st.markdown(f"**{me.name}**  \n{me.role.title()}")
        st.radio("Go to", allowed, key="page")
        if st.button("Log out"):
            st.session_state.clear()
            st.rerun()
    show_flash()
    PAGES[st.session_state.page](me)


with flask_app.app_context():
    main()
