"""Add tables for 5 modules: candidatures, pieces, taches, offres, institutions, attributions

Revision ID: f5a2c3d4e6
Revises: eb0aa4fff9b4
Create Date: 2026-04-26 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

# revision identifiers
revision = 'f5a2c3d4e6'
down_revision = 'eb0aa4fff9b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Candidatures ──
    op.create_table(
        'candidatures',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('ao_id', UUID(as_uuid=True), sa.ForeignKey('appels_offres.id'), nullable=False),
        sa.Column('abonne_id', UUID(as_uuid=True), sa.ForeignKey('abonnes.id'), nullable=False),
        sa.Column('statut', sa.String(30), server_default='en_veille', index=True),
        sa.Column('notes', sa.Text),
        sa.Column('montant_offre', sa.BigInteger),
        sa.Column('score_go_nogo', sa.Float),
        sa.Column('date_depot', sa.Date),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_candidatures_abonne', 'candidatures', ['abonne_id'])
    op.create_index('ix_candidatures_ao', 'candidatures', ['ao_id'])

    # ── Pièces administratives ──
    op.create_table(
        'pieces_administratives',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('abonne_id', UUID(as_uuid=True), sa.ForeignKey('abonnes.id'), nullable=False),
        sa.Column('type_piece', sa.String(50), nullable=False, index=True),
        sa.Column('nom_fichier', sa.String(255)),
        sa.Column('url_stockage', sa.Text),
        sa.Column('taille_fichier', sa.Integer),
        sa.Column('date_emission', sa.Date),
        sa.Column('date_expiration', sa.Date),
        sa.Column('est_valide', sa.Boolean, server_default='true'),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_pieces_abonne', 'pieces_administratives', ['abonne_id'])
    op.create_index('ix_pieces_expiration', 'pieces_administratives', ['date_expiration'])

    # ── Tâches candidature ──
    op.create_table(
        'taches_candidature',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('candidature_id', UUID(as_uuid=True), sa.ForeignKey('candidatures.id', ondelete='CASCADE'), nullable=False),
        sa.Column('titre', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('type_tache', sa.String(30), server_default='general'),
        sa.Column('priorite', sa.String(20), server_default='normale'),
        sa.Column('statut', sa.String(20), server_default='a_faire'),
        sa.Column('date_echeance', sa.Date),
        sa.Column('assignee_id', UUID(as_uuid=True), sa.ForeignKey('abonnes.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Offres générées (IA) ──
    op.create_table(
        'offres_generees',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('candidature_id', UUID(as_uuid=True), sa.ForeignKey('candidatures.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type_offre', sa.String(30), server_default='technique'),
        sa.Column('contenu_ia', sa.Text),
        sa.Column('prompt_utilise', sa.Text),
        sa.Column('version', sa.Integer, server_default='1'),
        sa.Column('valide_par_user', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Institutions ──
    op.create_table(
        'institutions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('nom', sa.String(255), nullable=False),
        sa.Column('sigle', sa.String(30)),
        sa.Column('slug', sa.String(255), unique=True, index=True),
        sa.Column('type_institution', sa.String(50)),
        sa.Column('secteurs', ARRAY(sa.String)),
        sa.Column('region', sa.String(100)),
        sa.Column('email_contact', sa.String(255)),
        sa.Column('telephone', sa.String(30)),
        sa.Column('site_web', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('logo_url', sa.Text),
        sa.Column('plan', sa.String(30), server_default='gratuit'),
        sa.Column('actif', sa.Boolean, server_default='true'),
        sa.Column('verifie', sa.Boolean, server_default='false'),
        sa.Column('abonne_id', UUID(as_uuid=True), sa.ForeignKey('abonnes.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Attributions (Transparence) ──
    op.create_table(
        'attributions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('ao_id', UUID(as_uuid=True), sa.ForeignKey('appels_offres.id'), nullable=True),
        sa.Column('attributaire', sa.String(255), nullable=False, index=True),
        sa.Column('montant_final', sa.BigInteger),
        sa.Column('date_signature', sa.Date),
        sa.Column('source_quotidien', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_attributions_ao', 'attributions', ['ao_id'])

    # ── Ajouter institution_id à appels_offres (si pas déjà fait) ──
    try:
        op.add_column('appels_offres', sa.Column('description_enrichie', sa.Text))
        op.add_column('appels_offres', sa.Column('contact_tel', sa.String(30)))
    except Exception:
        pass  # Colonnes déjà présentes


def downgrade() -> None:
    op.drop_table('attributions')
    op.drop_table('institutions')
    op.drop_table('offres_generees')
    op.drop_table('taches_candidature')
    op.drop_table('pieces_administratives')
    op.drop_table('candidatures')
    try:
        op.drop_column('appels_offres', 'description_enrichie')
        op.drop_column('appels_offres', 'contact_tel')
    except Exception:
        pass
