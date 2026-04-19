"""
NetSync Gov — Modèles SQLAlchemy
Tables : abonnes, appels_offres, preferences_alertes, favoris, paiements, envois_alertes, pipeline_logs, equipes
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, Integer, BigInteger, Date, DateTime,
    Text, Float, ForeignKey, ARRAY, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

def gen_uuid():
    return str(uuid.uuid4())

class Abonne(Base):
    __tablename__ = "abonnes"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    password_hash   = Column(String(255), nullable=False)
    prenom          = Column(String(100))
    nom             = Column(String(100))
    entreprise      = Column(String(255))
    whatsapp        = Column(String(30))
    plan            = Column(String(20), default="gratuit")
    actif           = Column(Boolean, default=True)
    email_verifie   = Column(Boolean, default=False)
    token_verification = Column(String(255))
    date_expiration_plan = Column(Date)
    plan_expire_le       = Column(Date)
    ao_consultes_auj     = Column(Integer, default=0)
    ao_consultes_reset_le = Column(Date)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    preferences     = relationship("PreferenceAlerte", back_populates="abonne", uselist=False)
    favoris         = relationship("Favori", back_populates="abonne")
    paiements       = relationship("Paiement", back_populates="abonne")

    @property
    def est_pro(self) -> bool:
        return self.plan in ("pro", "equipe")

class AppelOffre(Base):
    __tablename__ = "appels_offres"
    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference            = Column(String(255), index=True)
    titre                = Column(Text, nullable=False)
    autorite_contractante= Column(String(255), index=True)
    secteur              = Column(String(100), index=True)
    type_procedure       = Column(String(50))
    statut               = Column(String(30), default="ouvert", index=True)
    source               = Column(String(50), default="dgcmef")
    date_publication     = Column(Date, index=True)
    date_cloture         = Column(Date, index=True)
    montant_estime       = Column(BigInteger)
    description          = Column(Text)
    pdf_url              = Column(Text)
    est_urgent           = Column(Boolean, default=False)
    jours_restants       = Column(Integer)
    numero_quotidien     = Column(Integer)
    region               = Column(String(100))
    institution_id       = Column(UUID(as_uuid=True), nullable=True)
    contact_nom          = Column(String(255))
    contact_email        = Column(String(255))
    dao_disponible       = Column(Boolean, default=False)
    search_vector        = Column(Text)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    favoris              = relationship("Favori", back_populates="ao")
    envois               = relationship("EnvoiAlerte", back_populates="ao")

class PreferenceAlerte(Base):
    __tablename__ = "preferences_alertes"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    abonne_id   = Column(UUID(as_uuid=True), ForeignKey("abonnes.id"), unique=True)
    secteurs    = Column(ARRAY(String), default=[])
    mots_cles   = Column(ARRAY(String), default=[])
    canal_email = Column(Boolean, default=True)
    canal_whatsapp = Column(Boolean, default=False)
    heure_alerte   = Column(String(5), default="07:00")
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    abonne      = relationship("Abonne", back_populates="preferences")

class Favori(Base):
    __tablename__ = "favoris"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    abonne_id   = Column(UUID(as_uuid=True), ForeignKey("abonnes.id"))
    ao_id       = Column(UUID(as_uuid=True), ForeignKey("appels_offres.id"))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    abonne      = relationship("Abonne", back_populates="favoris")
    ao          = relationship("AppelOffre", back_populates="favoris")

class Paiement(Base):
    __tablename__ = "paiements"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    abonne_id       = Column(UUID(as_uuid=True), ForeignKey("abonnes.id"))
    transaction_id  = Column(String(255), unique=True, index=True)
    montant         = Column(Integer)
    devise          = Column(String(10), default="XOF")
    statut          = Column(String(30), default="en_attente")
    plan_achete     = Column(String(20))
    operateur       = Column(String(50))
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    abonne          = relationship("Abonne", back_populates="paiements")

class EnvoiAlerte(Base):
    __tablename__ = "envois_alertes"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    abonne_id   = Column(UUID(as_uuid=True), ForeignKey("abonnes.id"))
    ao_id       = Column(UUID(as_uuid=True), ForeignKey("appels_offres.id"))
    canal       = Column(String(20))
    statut      = Column(String(20), default="envoye")
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    abonne      = relationship("Abonne")
    ao          = relationship("AppelOffre", back_populates="envois")

class PipelineLog(Base):
    __tablename__ = "pipeline_logs"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_quotidien= Column(Integer)
    statut          = Column(String(20))
    nb_ao_extraits  = Column(Integer, default=0)
    nb_ao_nouveaux  = Column(Integer, default=0)
    nb_alertes      = Column(Integer, default=0)
    erreur          = Column(Text)
    duree_secondes  = Column(Float)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

class Equipe(Base):
    __tablename__ = "equipes"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom         = Column(String(255))
    admin_id    = Column(UUID(as_uuid=True), ForeignKey("abonnes.id"))
    plan        = Column(String(20), default="equipe")
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
