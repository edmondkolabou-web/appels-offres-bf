"""
NetSync Gov — Schémas Pydantic (validation requête/réponse)
"""
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Appels d'offres ────────────────────────────────────────────────────────────
class AOBase(BaseModel):
    reference:             str
    titre:                 str
    autorite_contractante: str
    type_procedure:        str
    secteur:               str
    statut:                str
    source:                str
    date_publication:      date
    date_cloture:          Optional[date] = None
    montant_estime:        Optional[int]  = None
    numero_quotidien:      Optional[int]  = None

class AODetail(AOBase):
    id:          UUID
    description: Optional[str] = None
    pdf_url:     Optional[str] = None
    created_at:  datetime
    est_urgent:  bool = False
    jours_restants: Optional[int] = None

    model_config = {"from_attributes": True}

class AOListItem(AOBase):
    id:          UUID
    est_urgent:  bool = False
    jours_restants: Optional[int] = None

    model_config = {"from_attributes": True}

class AOFilters(BaseModel):
    q:              Optional[str]  = Field(None, description="Recherche full-text")
    secteur:        Optional[str]  = None
    statut:         Optional[str]  = "ouvert"
    source:         Optional[str]  = None
    type_procedure: Optional[str]  = None
    date_debut:     Optional[date] = None
    date_fin:       Optional[date] = None
    montant_min:    Optional[int]  = None
    montant_max:    Optional[int]  = None
    urgent_only:    bool           = False
    page:           int            = Field(1, ge=1)
    per_page:       int            = Field(20, ge=1, le=100)

class AOListResponse(BaseModel):
    items:      List[AOListItem]
    total:      int
    page:       int
    per_page:   int
    pages:      int


# ── Auth ───────────────────────────────────────────────────────────────────────
class RegisterIn(BaseModel):
    email:      EmailStr
    password:   str = Field(min_length=8)
    prenom:     str = Field(min_length=1, max_length=100)
    nom:        str = Field(min_length=1, max_length=100)
    entreprise: Optional[str] = None
    whatsapp:   Optional[str] = None
    plan:       str = Field("gratuit", pattern="^(gratuit|pro|equipe)$")
    secteurs:   List[str] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mot de passe trop court (8 caractères minimum)")
        return v

class LoginIn(BaseModel):
    email:    EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    abonne_id:    str
    plan:         str

class AbonneOut(BaseModel):
    id:          UUID
    email:       str
    prenom:      str
    nom:         str
    entreprise:  Optional[str] = None
    whatsapp:    Optional[str] = None
    plan:        str
    est_pro:     bool
    created_at:  datetime

    model_config = {"from_attributes": True}

class AbonneUpdate(BaseModel):
    prenom:     Optional[str] = None
    nom:        Optional[str] = None
    entreprise: Optional[str] = None
    whatsapp:   Optional[str] = None


# ── Alertes ────────────────────────────────────────────────────────────────────
class AlerteIn(BaseModel):
    secteurs:   List[str] = Field(default_factory=list)
    mots_cles:  List[str] = Field(default_factory=list)
    sources:    List[str] = Field(default_factory=list)
    canal:      str = Field("les_deux", pattern="^(email|whatsapp|les_deux)$")
    rappel_j3:  bool = True

class AlerteOut(BaseModel):
    id:         UUID
    secteurs:   List[str]
    mots_cles:  List[str]
    sources:    List[str]
    canal:      str
    rappel_j3:  bool
    actif:      bool
    created_at: datetime

    model_config = {"from_attributes": True}

class AlerteUpdate(BaseModel):
    secteurs:   Optional[List[str]] = None
    mots_cles:  Optional[List[str]] = None
    sources:    Optional[List[str]] = None
    canal:      Optional[str]       = None
    rappel_j3:  Optional[bool]      = None
    actif:      Optional[bool]      = None


# ── Favoris ────────────────────────────────────────────────────────────────────
class FavoriIn(BaseModel):
    ao_id: UUID
    note:  Optional[str] = None

class FavoriOut(BaseModel):
    id:      UUID
    ao:      AOListItem
    note:    Optional[str] = None
    cree_le: datetime

    model_config = {"from_attributes": True}


# ── Paiements ──────────────────────────────────────────────────────────────────
class PaiementIn(BaseModel):
    plan:    str = Field(..., pattern="^(pro|equipe)$")
    periode: str = Field(..., pattern="^(mensuel|annuel)$")
    methode: str = Field(..., pattern="^(om|moov|card)$")

class PaiementOut(BaseModel):
    id:             UUID
    transaction_id: str
    montant:        int
    plan:           str
    periode:        str
    methode:        str
    statut:         str
    expire_le:      Optional[date] = None
    created_at:     datetime

    model_config = {"from_attributes": True}

class CinetPayWebhookIn(BaseModel):
    transaction_id: str
    status:         str
    metadata:       Optional[dict] = None


# ── Admin ──────────────────────────────────────────────────────────────────────
class PipelineRunOut(BaseModel):
    run_at:           str
    pdfs_traites:     int
    ao_extraits:      int
    ao_inseres:       int
    ao_mis_a_jour:    int
    alertes_envoyees: int
    erreurs:          List[str]
    duree_sec:        float

class PipelineLogOut(BaseModel):
    id:               UUID
    numero_quotidien: int
    statut:           str
    ao_extraits:      int
    ao_nouveaux:      int
    duree_ms:         Optional[int] = None
    run_at:           datetime

    model_config = {"from_attributes": True}

class StatsOut(BaseModel):
    total_ao:        int
    ao_ouverts:      int
    ao_ce_mois:      int
    total_abonnes:   int
    abonnes_pro:     int
    alertes_envoyees_7j: int
