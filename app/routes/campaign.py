import json
import threading
from datetime import datetime

from flask import Blueprint, request, jsonify

from ..config import CONFIG
from ..database import log_event

campaign_bp = Blueprint('campaign', __name__)


@campaign_bp.route('/api/campaign/create', methods=['POST'])
def api_campaign_create():
    from campaign_manager import Campaign, init_campaign_db
    init_campaign_db()
    data = request.get_json(force=True, silent=True) or {}
    name = data.get('name', 'Campagne ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    scenario = data.get('scenario', 'classement')
    email_template = data.get('email_template', '1')

    camp = Campaign(name, scenario, email_template)
    camp.status = 'draft'

    targets = data.get('targets', [])
    for t in targets:
        camp.add_target(t.get('email', ''), t.get('pseudo', ''), t.get('ville', ''))

    camp.save_to_db()
    log_event("CAMPAIGN_CREATED", camp.id, {"name": name, "targets": len(targets)})
    return jsonify({"ok": True, "campaign_id": camp.id, "name": name, "targets": len(targets)})


@campaign_bp.route('/api/campaign/list')
def api_campaign_list():
    from campaign_manager import Campaign, init_campaign_db
    init_campaign_db()
    rows = Campaign.list_all()
    campaigns = []
    for r in rows:
        campaigns.append({
            "id": r[0], "name": r[1], "status": r[2],
            "targets": r[3], "sent": r[4], "captured": r[5],
            "created": r[6], "scheduled": r[7]
        })
    return jsonify({"campaigns": campaigns})


@campaign_bp.route('/api/campaign/launch', methods=['POST'])
def api_campaign_launch():
    data = request.get_json(force=True, silent=True) or {}
    campaign_id = data.get('campaign_id', '')
    if not campaign_id:
        return jsonify({"ok": False, "error": "campaign_id requis"}), 400

    smtp_user = data.get('smtp_user', '')
    smtp_pass = data.get('smtp_pass', '')

    from campaign_manager import Campaign, send_bulk, init_campaign_db
    init_campaign_db()
    camp = Campaign.load_from_db(campaign_id)
    if not camp:
        return jsonify({"ok": False, "error": "Campagne introuvable"}), 404

    base_url = "http://127.0.0.1:{}".format(CONFIG.get("SERVER_PORT", 8080))

    def do_send():
        try:
            send_bulk(campaign_id, smtp_user, smtp_pass, base_url, delay=1)
        except Exception as e:
            print("[CAMPAIGN] send error:", e)

    t = threading.Thread(target=do_send, daemon=True)
    t.start()

    return jsonify({"ok": True, "campaign_id": camp.id, "targets": len(camp.targets)})


@campaign_bp.route('/api/campaign/stats')
def api_campaign_stats():
    from campaign_manager import Campaign, init_campaign_db
    init_campaign_db()
    rows = Campaign.list_all()
    total = len(rows)
    active = sum(1 for r in rows if r[2] in ('scheduled', 'running'))
    total_sent = sum(r[4] for r in rows)
    total_captured = sum(r[5] for r in rows)
    return jsonify({
        "total_campaigns": total,
        "active_campaigns": active,
        "total_sent": total_sent,
        "total_captured": total_captured,
    })


@campaign_bp.route('/api/campaign/<campaign_id>')
def api_campaign_detail(campaign_id):
    from campaign_manager import Campaign, init_campaign_db
    init_campaign_db()
    camp = Campaign.load_from_db(campaign_id)
    if not camp:
        return jsonify({"error": "Campagne introuvable"}), 404
    return jsonify({
        "id": camp.id,
        "name": camp.name,
        "scenario": camp.scenario,
        "email_template": camp.email_template,
        "status": camp.status,
        "targets": len(camp.targets),
        "sent": camp.sent_count,
        "captured": camp.captured_count,
        "scheduled": str(camp.scheduled_at) if camp.scheduled_at else None,
    })
