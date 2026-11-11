# Schema objects

We use [Pydantic](https://docs.pydantic.dev/2.0/) schemas heavily throughout the
backend service codebase.

They are used in two primary ways:

1. For handling database-related data objects beyond the scope of SQLAlchemy or
   a transaction and into application logic and HTTP requests, eg a User or
   Export. See below for more info
2. To provide structure to reusable objects, eg a JsonResponse or
   CommonQueryParams

Pydantic schemas are used vs alternatives like Python's built-in dataclasses
because they are fantastically useful in both the above cases - for many
reasons, including but not limited to:

-   FastAPI's direct support for Pydantic models
-   Field and model validation capabilities
-   Enforced type hinting
-   Customisability and extendability
-   Lots of utility functions

All schemas should live in the
[`src/backend/app/schemas/` directory](src/backend/app/schemas/).

## Database-related schemas

These schemas follow a many-to-one relationship with their related database
model, that is many schema versions to one database model. For example, we have
a [Export](src/backend/app/models/export/export.py) database model (representing
an `exports` table in the database) but there will be a number of Pydantic
schemas used to represent this entity in different contexts. The schemas used
follow a specific pattern resulting in four (for now) schema variants. Following
the Export example, these would be:

-   An `ExportBase` schema - a common parent inherited by the other schemas, not
    intended for direct use elsewhere
-   An `ExportDB` schema - a 1:1 representation of the fields database
    model/table, safe for use within the application
-   An `ExportRead` schema - a slimmed down representation used in API responses
    only including fields explicitly intended to be shared externally
-   An `ExportUpdate` schema - the most lightweight of all with all fields
    optional used to partially update objects in `PATCH` requests

The relationship between the schemas is based on class inheritance and therefore
some caution needs to be paid to the additive nature of where properties and
types are defined. In some cases Python `Generic` is used to enable flexbility.

Depending on the complexity of an entity, its properties and relationships,
these schemas will look different and be implemented differently. In the
simplest form (eg the `ExportStatus` schemas in
[`src/backend/app/schemas/export/export.py`](src/backend/app/schemas/export/export.py))
the full extent of the schema definition is defined in the `Base` schema and all
other schemas simply inherit from the `Base` with no additions.

### `Base` schema

This should inherit from `BaseSchema` in [`base.py`](base.py) to ensure
consistency.

From there, any properties that are common to all other schemas can be defined.
Note that you can't remove a property or change it's type from another schema
later once it's inherited from this `Base`.

For properties that require typing flexbility, `Generic` parameterisation can
also be defined here. To facilitate this you will need to create a `TypeVar` and
then subclass both `BaseSchema` and your new `TypeVar` like:

```python
ExportStatusType = TypeVar("ExportStatusType")

...

class ExportBase(BaseSchema, Generic[ExportStatusType]):

    statuses: list[ExportStatusType] = Field(default_factory=list)
    ...
```

Other schemas can now subclass this `Base` schema passing in the appropriate
class parameter:

```python
class ExportDB(ExportBase[ExportStatusDB]):
    ...
```

### `DB` schema

This schema acts as the bridge between where SQLAlchemy's Object Relational
Mapper (ORM) ends and the rest of the backend application continues, and as such
it should be an almost exact one-to-one mapping of the fields present on the
database model. This allows us to load a record from the database via a query
and then easily exchange it into a format that rest of the application and
FastAPI can work with via `model_validate()`, as easily as:

```python
query = select(Export).where(Export.org_uid == org_uid)
rows = session.execute(query).scalars().all()
return [ExportDB.model_validate(row) for row in rows]
```

And vice versa to insert or update a database record with `model_dump()`:

```python
export_schema = ExportDB(...<data>...)
with db.get_session() as session:
    session.add(Export(**export_schema.model_dump()))
    session.commit()
```

### `Read` schema

This schema is used at the point of interaction with the outside world (even
other services) and only includes a subset of the properties available on a
database model based on what we want to or what is safe to surface externally.
This is useful because there are usually fields present that aren't intended for
the "user" of the API to consume but are still needed within the application. An
example of this is the `authorised_email_domains` property of an Organisation -
needed internally, but not something we want the user to see. Fields may also be
loaded from the database in one format but require reformatting in order to be
served correctly.

The
[`response_model` argument](https://fastapi.tiangolo.com/tutorial/response-model/#response_model-parameter)
set in FastAPI endpoint path operation decorator should almost always be a
`Read` schema. This enables FastAPI to proactively validate and filter the data
in the response, even if you return a different schema. Eg your code might
return an `ExportDB` schema it just loaded from the database, but
`reponse_model=ExportRead` in the path decorator so extraneous properties are
filtered and the API returns the intended output.

As such, even if there is no difference in the properties on the `DB` schema vs
what would be the `Read` schema, it is still worthwhile to create and use one as
this should make you consciously consider what data is being sent to API
consumers.

### `Update` schema

For API resources that allow updates to records we should define an `Update`
schema. This represents the JSON the API could receive in an update `PATCH`
request. This one's a little different in that it should only include properties
that are possible to be updated by an API user, and generally all optional so
any of the allowed properties can be updated alone or together. Since the global
`BaseSchema` includes `uid`, `created_at` and `updated_at` fields the `Update`
schema probably shouldn't subclass `BaseSchema`.

### `Create` schema!?!

Those of you paying attention might have thought "great, but where's the C for
my CRUD?". And yes, we can also add a `Create` schema when API functionality is
required to support creating any given resource which is expected in future.
Watch this space...

(And before you ask, no one likes `DELETE` requests. Update a status field or
boolean flag instead)
