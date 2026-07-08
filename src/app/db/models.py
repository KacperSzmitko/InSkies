from datetime import datetime
from sqlalchemy import ForeignKey, func, JSON, String, TIMESTAMP, NUMERIC, DATE
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


########## Application Models ##########


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str] = mapped_column(String(256), unique=True)
    password_hash: Mapped[str] = mapped_column(String(64))
    user_role_id: Mapped[int] = mapped_column(ForeignKey("user_roles.id", ondelete="RESTRICT"))
    bio: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    user_role: Mapped["UserRole"] = relationship(back_populates="users")
    projects: Mapped[list["Project"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    equipment_lists: Mapped[list["EquipmentList"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    project_likes: Mapped[list["ProjectLike"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    project_comments: Mapped[list["ProjectComment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    comment_likes: Mapped[list["CommentLike"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    frame_collections: Mapped[list["FrameCollection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)

    users: Mapped[list["User"]] = relationship(back_populates="user_role")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(256))
    final_image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id", ondelete="SET NULL"))
    description: Mapped[str | None]
    equipment_list_id: Mapped[int | None] = mapped_column(ForeignKey("equipment_lists.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="projects")
    final_image: Mapped["Image | None"] = relationship(back_populates="featured_in_projects")
    equipment_list: Mapped["EquipmentList | None"] = relationship(back_populates="projects")
    likes: Mapped[list["ProjectLike"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    comments: Mapped[list["ProjectComment"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    frame_collection_links: Mapped[list["ProjectFrameCollection"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    edit_histories: Mapped[list["EditHistory"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )


class EquipmentList(Base):
    __tablename__ = "equipment_lists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(256))
    telescope: Mapped[str | None] = mapped_column(String(512))
    mount: Mapped[str | None] = mapped_column(String(512))
    camera: Mapped[str | None] = mapped_column(String(512))
    filters: Mapped[str | None] = mapped_column(String(512))
    guide_telescope: Mapped[str | None] = mapped_column(String(512))
    guide_camera: Mapped[str | None] = mapped_column(String(512))
    other: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="equipment_lists")
    projects: Mapped[list["Project"]] = relationship(back_populates="equipment_list")


class ProjectLike(Base):
    __tablename__ = "project_likes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())

    user: Mapped["User"] = relationship(back_populates="project_likes")
    project: Mapped["Project"] = relationship(back_populates="likes")


class ProjectComment(Base):
    __tablename__ = "project_comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    comment_text: Mapped[str]
    response_to_id: Mapped[int | None] = mapped_column(ForeignKey("project_comments.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="project_comments")
    project: Mapped["Project"] = relationship(back_populates="comments")
    response_to: Mapped["ProjectComment | None"] = relationship(
        remote_side="ProjectComment.id", back_populates="replies"
    )
    replies: Mapped[list["ProjectComment"]] = relationship(back_populates="response_to")
    likes: Mapped[list["CommentLike"]] = relationship(
        back_populates="comment", cascade="all, delete-orphan", passive_deletes=True
    )


class CommentLike(Base):
    __tablename__ = "comment_likes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    comment_id: Mapped[int] = mapped_column(ForeignKey("project_comments.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())

    user: Mapped["User"] = relationship(back_populates="comment_likes")
    comment: Mapped["ProjectComment"] = relationship(back_populates="likes")


########## Editor Models ##########


class Frame(Base):
    __tablename__ = "frames"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(256))
    storage_location_id: Mapped[int] = mapped_column(ForeignKey("storage_locations.id", ondelete="RESTRICT"))
    frame_collection_id: Mapped[int] = mapped_column(ForeignKey("frame_collections.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    storage_location: Mapped["StorageLocation"] = relationship(back_populates="frames")
    frame_collection: Mapped["FrameCollection"] = relationship(back_populates="frames")


class FrameCollection(Base):
    __tablename__ = "frame_collections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(256))
    frames_type_id: Mapped[int] = mapped_column(ForeignKey("frames_types.id", ondelete="RESTRICT"))
    exposure_time: Mapped[float | None] = mapped_column(NUMERIC)
    binning: Mapped[int | None]
    gain: Mapped[float | None] = mapped_column(NUMERIC)
    iso: Mapped[int | None]
    filter: Mapped[str | None] = mapped_column(String(256))
    temperature: Mapped[float | None] = mapped_column(NUMERIC)
    capture_location: Mapped[str | None] = mapped_column(String(256))
    capture_date: Mapped[datetime | None] = mapped_column(DATE)
    notes: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="frame_collections")
    frames_type: Mapped["FramesType"] = relationship(back_populates="frame_collections")
    frames: Mapped[list["Frame"]] = relationship(
        back_populates="frame_collection", cascade="all, delete-orphan", passive_deletes=True
    )
    project_links: Mapped[list["ProjectFrameCollection"]] = relationship(
        back_populates="frame_collection", cascade="all, delete-orphan", passive_deletes=True
    )


class FramesType(Base):
    __tablename__ = "frames_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)

    frame_collections: Mapped[list["FrameCollection"]] = relationship(back_populates="frames_type")


class ProjectFrameCollection(Base):
    __tablename__ = "projects_frame_collections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    frame_collection_id: Mapped[int] = mapped_column(ForeignKey("frame_collections.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())

    project: Mapped["Project"] = relationship(back_populates="frame_collection_links")
    frame_collection: Mapped["FrameCollection"] = relationship(back_populates="project_links")


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(256))
    storage_location_id: Mapped[int] = mapped_column(ForeignKey("storage_locations.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    storage_location: Mapped["StorageLocation"] = relationship(back_populates="images")
    featured_in_projects: Mapped[list["Project"]] = relationship(back_populates="final_image")
    edit_histories_as_output: Mapped[list["EditHistory"]] = relationship(back_populates="output_image")


class StorageLocation(Base):
    __tablename__ = "storage_locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(256))

    frames: Mapped[list["Frame"]] = relationship(back_populates="storage_location")
    images: Mapped[list["Image"]] = relationship(back_populates="storage_location")


class EditHistory(Base):
    __tablename__ = "edit_histories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"))
    operation_arguments: Mapped[dict | None] = mapped_column(JSON)
    order: Mapped[int]
    output_image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="edit_histories")
    operation: Mapped["Operation"] = relationship(back_populates="edit_histories")
    output_image: Mapped["Image | None"] = relationship(back_populates="edit_histories_as_output")


########## Operator Models ##########


class Operation(Base):
    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256))
    parameters: Mapped[dict | None] = mapped_column(JSON)
    reverse_operation_id: Mapped[int | None] = mapped_column(ForeignKey("operations.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=func.now(), onupdate=func.now())

    reverse_operation: Mapped["Operation | None"] = relationship(
        remote_side="Operation.id", back_populates="reversed_by"
    )
    reversed_by: Mapped[list["Operation"]] = relationship(back_populates="reverse_operation")
    edit_histories: Mapped[list["EditHistory"]] = relationship(back_populates="operation")
