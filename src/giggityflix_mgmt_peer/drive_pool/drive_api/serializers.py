from rest_framework import serializers

from giggityflix_mgmt_peer.drive_pool.models.drive_models import PhysicalDrive, Partition


class PartitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partition
        fields = ['mount_point', 'created_at', 'updated_at']


class PhysicalDriveSerializer(serializers.ModelSerializer):
    partitions = PartitionSerializer(many=True, read_only=True)

    class Meta:
        model = PhysicalDrive
        fields = [
            'id', 'manufacturer', 'model', 'serial',
            'size_bytes', 'filesystem_type',
            'detected_at', 'updated_at', 'partitions'
        ]


class DriveStatsSerializer(serializers.Serializer):
    total_drives = serializers.IntegerField()
    total_partitions = serializers.IntegerField()
    total_storage_bytes = serializers.IntegerField()
