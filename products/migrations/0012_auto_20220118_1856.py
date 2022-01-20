# Generated by Django 3.2.9 on 2022-01-18 18:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_auto_20220118_1849'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='productinventory',
            options={},
        ),
        migrations.AddConstraint(
            model_name='productinventory',
            constraint=models.UniqueConstraint(fields=('product', 'product_colour', 'size'), name='product_inventory_constraint'),
        ),
    ]
