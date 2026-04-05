using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace AudioProcessing.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class UpdatedTrackTable : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.RenameColumn(
                name: "storage_key",
                table: "Tracks",
                newName: "output_key");

            migrationBuilder.AddColumn<string>(
                name: "input_key",
                table: "Tracks",
                type: "text",
                nullable: false,
                defaultValue: "");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "input_key",
                table: "Tracks");

            migrationBuilder.RenameColumn(
                name: "output_key",
                table: "Tracks",
                newName: "storage_key");
        }
    }
}
