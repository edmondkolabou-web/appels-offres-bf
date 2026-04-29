"""
NetSync Gov — Modèles SQLAlchemy
"""
import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Boolean,
    Date, DateTime, ForeignKey, CheckConstraint, UniqueConstraint,
    Index, func, event
)
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class AppelOffre(Base):
    """Table principale — appels d'offres parsés depuis les sources."""
    __tablename__ = "appels_offres"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference             = Column(String(100), nullable=False, unique=True, index=True)
    titre                 = Column(Text, nullable=False)
    description           = Column(Text)
    autorite_contractante = Column(String(200), nullable=False, index=True)
    type_procedure        = Column(String(20), nullable=False,
                                   comment="ouvert|restreint|dpx|ami|rfp|rfq")
    secteur               = Column(String(50), nullable=False, index=True)
    statut                = Column(String(20), nullable=False, default="ouvert",
                                   comment="ouvert|cloture|attribue|annule")
    date_publication      = Column(Date, nullable=False, index=True)
    date_cloture          = Column(Date, index=True)
    montant_estime        = Column(BigInteger, comment="FCFA")
    source                = Column(String(30), comment="dgcmef|cci_bf|undp|bm_step")
    pdf_url               = Column(Text)
    numero_quotidien      = Column(Integer)
    search_vector         = Column(TSVECTOR)
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), server_default=func.now(),
                                   onupdate=func.now())

    # Relations
    envois     = relationship("EnvoiAlerte", back_populates="ao", cascade="all, delete-orphan")
    favoris    = relationship("Favori", back_populates="ao", cascade="all, delete-orphan")

    # Contraintes
    __table_args__ = (
        CheckConstraint(
            "type_procedure IN ('ouvert','restreint','dpx','ami','rfp','rfq')",
            name="chk_type_procedure"
        ),
        CheckConstraint(
            "statut IN ('ouvert','cloture','attribue','annule')",
            name="chk_statut"
        ),
        CheckConstraint(
            "source IN ('dgcmef','cci_bf','undp','bm_step')",
            name="chk_source"
        ),
        # Index composé source + date
        Index("idx_ao_source_date", "source", "date_publication"),
        # Index GIN full-text
        Index("idx_ao_search_vector", "search_vector", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<AppelOffre ref={self.reference!r} titre={self.titre[:40]!r}>"

    @property
    def est_urgent(self) -> bool:
        """Retourne True si clôture dans <= 3 jours."""
        if not self.date_cloture:
            return False
        delta = (self.date_cloture - date.today()).days
        return 0 <= delta <= 3

    @property
    def jours_restants(self) -> Optional[int]:
        """Nombre de jours avant clôture."""
        if not self.date_cloture:
            return None
        return (self.date_cloture - date.today()).days


class Abonne(Base):
    """Utilisateurs abonnés à la plateforme."""
    __tablename__ = "abonnes"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email            = Column(String(255), nullable=False, unique=True, index=True)
    password_hash    = Column(String(255), comment="bcrypt hash")
    prenom           = Column(String(100), nullable=False)
    nom              = Column(String(100), nullable=False)
    entreprise       = Column(String(200))
    whatsapp         = Column(String(20), index=True)
    plan             = Column(String(10), nullable=False, default="gratuit",
                              comment="gratuit|pro|equipe")
    plan_expire_le   = Column(Date)
    ao_consultes_auj = Column(Integer, nullable=False, default=0)
    email_verified   = Column(Boolean, nullable=False, default=False)
    actif            = Column(Boolean, nullable=False, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    preferences = relationship("PreferenceAlerte", back_populates="abonne",
                               cascade="all, delete-orphan")
    envois      = relationship("EnvoiAlerte", back_populates="abonne")
    favoris     = relationship("Favori", back_populates="abonne",
                               cascade="all, delete-orphan")
    paiements   = relationship("Paiement", back_populates="abonne")

    __table_args__ = (
        CheckConstraint("plan IN ('gratuit','pro','equipe')", name="chk_plan"),
        Index("idx_abonne_whatsapp", "whatsapp",
              postgresql_where="whatsapp IS NOT NULL"),
    )

    @property
    def est_pro(self) -> bool:
        return self.plan in ("pro", "equipe") and (
            self.plan_expire_le is None or self.plan_expire_le >= date.today()
        )

    @property
    def peut_consulter(self) -> bool:
        """Gratuit : max 3 AO/jour. Pro : illimité."""
        if self.est_pro:
            return True
        return self.ao_consultes_auj < 3


class PreferenceAlerte(Base):
    """Configuration des alertes par abonné."""
    __tablename__ = "preferences_alertes"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    abonne_id  = Column(UUID(as_uuid=True), ForeignKey("abonnes.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    secteurs   = Column(ARRAY(String), default=list, comment="Liste de secteurs surveillés")
    mots_cles  = Column(ARRAY(String), default=list, comment="Mots-clés personnalisés")
    sources    = Column(ARRAY(String), default=list, comment="Sources à surveiller")
    canal      = Column(String(20), nullable=False, default="les_deux",
                        comment="email|whatsapp|les_deux")
    rappel_j3  = Column(Boolean, nullable=False, default=True)
    actif      = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    abonne = relationship("Abonne", back_populates="preferences")

    __table_args__ = (
        CheckConstraint("canal IN ('email','whatsapp','les_deux')", name="chk_canal"),
        Index("idx_alerte_secteurs", "secteurs", postgresql_using="gin"),
    )

    def match_ao(self, ao: AppelOffre) -> bool:
        """Vérifie si un AO correspond aux préférences de l'abonné."""
        if not self.actif:
            return False
        # Match secteur
        if self.secteurs and ao.secteur not in self.secteurs:
            # Vérifier les mots-clés en fallback
            if not self.mots_cles:
                return False
            texte = f"{ao.titre} {ao.description or ''}".lower()
            if not any(kw.lower() in texte for kw in self.mots_cles):
                return False
        # Match source
        if self.sources and ao.source not in self.sources:
            return False
        return True


class EnvoiAlerte(Base):
    """Log de chaque alerte envoyée."""
    __tablename__ = "envois_alertes"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    abonne_id   = Column(UUID(as_uuid=True), ForeignKey("abonnes.id"), nullable=False, index=True)
    ao_id       = Column(UUID(as_uuid=True), ForeignKey("appels_offres.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    canal       = Column(String(20), nullable=False, comment="email|whatsapp")
    statut      = Column(String(20), nullable=False, default="envoye",
                         comment="envoye|echec|reessai")
    type_alerte = Column(String(30), nullable=False,
                         comment="nouveau_ao|rappel_j3|attribution")
    tentatives  = Column(Integer, nullable=False, default=0)
    erreur      = Column(Text)
    envoye_le   = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    abonne = relationship("Abonne", back_populates="envois")
    ao     = relationship("AppelOffre", back_populates="envois")

    __table_args__ = (
        CheckConstraint("canal IN ('email','whatsapp')", name="chk_envoi_canal"),
        CheckConstraint("statut IN ('envoye','echec','reessai')", name="chk_envoi_statut"),
        # Éviter les doublons d'envoi même AO/abonné/canal
        UniqueConstraint("abonne_id", "ao_id", "canal", "type_alerte", name="uq_envoi"),
        Index("idx_envoi_abonne_ao", "abonne_id", "ao_id"),
        Index("idx_envoi_statut", "statut"),
    )


class Favori(Base):
    """AO sauvegardés par un abonné."""
    __tablename__ = "favoris"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    abonne_id = Column(UUID(as_uuid=True), ForeignKey("abonnes.id", ondelete="CASCADE"),
                       nullable=False)
    ao_id     = Column(UUID(as_uuid=True), ForeignKey("appels_offres.id", ondelete="CASCADE"),
                       nullable=False)
    note      = Column(Text, comment="Note privée de l'abonné")
    cree_le   = Column(DateTime(timezone=True), server_default=func.now())

    abonne = relationship("Abonne", back_populates="favoris")
    ao     = relationship("AppelOffre", back_populates="favoris")

    __table_args__ = (
        UniqueConstraint("abonne_id", "ao_id", name="uq_favori"),
    )


class PipelineLog(Base):
    """Monitoring du pipeline PDF quotidien."""
    __tablename__ = "pipeline_logs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_quotidien = Column(Integer, nullable=False, unique=True, index=True)
    statut           = Column(String(20), nullable=False,
                              comment="succes|echec|partiel")
    nb_ao_extraits   = Column(Integer, nullable=False, default=0)
    nb_ao_nouveaux   = Column(Integer, nullable=False, default=0)
    duree_secondes   = Column(Integer)
    erreur           = Column(Text)
    nb_alertes       = Column(Integer, default=0)
    nb_alertes       = Column(Integer, default=0)
    nb_alertes       = Column(Integer, default=0)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        CheckConstraint("statut IN ('succes','echec','partiel')", name="chk_pipeline_statut"),
    )


class Paiement(Base):
    """Transactions CinetPay."""
    __tablename__ = "paiements"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    abonne_id      = Column(UUID(as_uuid=True), ForeignKey("abonnes.id"), nullable=False, index=True)
    transaction_id = Column(String(100), nullable=False, unique=True, index=True,
                            comment="ID CinetPay — idempotence webhook")
    montant        = Column(Integer, nullable=False, comment="FCFA")
    plan           = Column(String(10), nullable=False, comment="pro|equipe")
    periode        = Column(String(10), nullable=False, comment="mensuel|annuel")
    methode        = Column(String(10), nullable=False, comment="om|moov|card")
    statut         = Column(String(20), nullable=False, default="pending",
                            comment="pending|success|failed|refunded")
    metadata_      = Column("metadata", JSONB, default=dict)
    expire_le      = Column(Date, comment="Fin abonnement calculée")
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    abonne = relationship("Abonne", back_populates="paiements")

    __table_args__ = (
        CheckConstraint("plan IN ('pro','equipe')", name="chk_paiement_plan"),
        CheckConstraint("periode IN ('mensuel','annuel')", name="chk_paiement_periode"),
        CheckConstraint("statut IN ('pending','success','failed','refunded')", name="chk_paiement_statut"),
        Index("idx_paiement_statut", "statut"),
    )
