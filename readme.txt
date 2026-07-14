Repository Rule #1

Repositories returning ORM objects that will be serialized
must eagerly load every required relationship.

Never rely on SQLAlchemy lazy loading
inside AsyncSession.

Use joinedload/selectinload
inside repositories.