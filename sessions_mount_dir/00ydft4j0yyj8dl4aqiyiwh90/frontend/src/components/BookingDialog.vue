<template>
  <v-dialog v-model="dialog" max-width="600px">
    <template v-slot:activator="{ on, attrs }">
      <v-btn color="primary" v-bind="attrs" v-on="on">
        预约课程
      </v-btn>
    </template>
    <v-card>
      <v-card-title>
        <span class="text-h5">课程预约</span>
      </v-card-title>
      <v-card-text>
        <v-container>
          <v-form ref="form" v-model="valid" lazy-validation>
            <v-row>
              <v-col cols="12" sm="6" md="4">
                <v-select
                  v-model="selectedCourse"
                  :items="courses"
                  item-text="name"
                  item-value="id"
                  label="选择课程"
                  required
                  :rules="[v => !!v || '请选择课程']"
                ></v-select>
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="memberId"
                  label="会员ID"
                  required
                  :rules="[v => !!v || '请输入会员ID']"
                ></v-text-field>
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="bookingTime"
                  label="预约时间"
                  type="datetime-local"
                  required
                  :rules="[v => !!v || '请选择预约时间']"
                ></v-text-field>
              </v-col>
            </v-row>
          </v-form>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-alert
          v-if="errorMessage"
          type="error"
          dense
          class="mb-4"
        >
          {{ errorMessage }}
        </v-alert>
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" text @click="closeDialog">
          取消
        </v-btn>
        <v-btn 
          color="blue darken-1" 
          text 
          @click="submitBooking" 
          :disabled="!valid || isLoading"
          :loading="isLoading"
        >
          {{ isLoading ? '处理中...' : '确认预约' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref } from 'vue';
import { useStore } from 'vuex';
import { postBooking } from '../api/bookings';
import { getMemberById } from '../api/members';

export default {
  name: 'BookingDialog',
  props: {
    courses: {
      type: Array,
      required: true,
      default: () => []
    }
  },
  setup(props, { emit }) {
    const dialog = ref(false);
    const valid = ref(false);
    const form = ref(null);
    const selectedCourse = ref(null);
    const memberId = ref('');
    const bookingTime = ref('');
const isLoading = ref(false);
    const errorMessage = ref('');
    const store = useStore();

    const closeDialog = () => {
      dialog.value = false;
      if (form.value) {
        form.value.reset();
      }
    };

    const submitBooking = async () => {
      if (form.value.validate()) {
        try {
          const bookingData = {
            member_id: memberId.value,
            course_id: selectedCourse.value,
            booking_time: bookingTime.value,
            status: 'confirmed'
          };
          
          await postBooking(bookingData);
          store.dispatch('showSnackbar', {
            message: '预约成功',
            color: 'success'
          });
          emit('booking-success');
          closeDialog();
        } catch (error) {
          store.dispatch('showSnackbar', {
            message: '预约失败: ' + error.message,
            color: 'error'
          });
        }
      }
    };

    return {
      dialog,
      valid,
      form,
      selectedCourse,
      memberId,
      bookingTime,
      isLoading,
      errorMessage,
      closeDialog,
      submitBooking
    };
  }
};
</script>

<style scoped>
.v-card {
  padding: 20px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    const submitBooking = async () => {
      if (form.value.validate()) {
        isLoading.value = true;
        errorMessage.value = '';
        try {
          // 验证会员ID是否存在
          const member = await getMemberById(memberId.value);
          if (!member) {
            throw new Error('会员ID不存在');
          }

          const bookingData = {
            member_id: memberId.value,
            course_id: selectedCourse.value,
            booking_time: bookingTime.value,
            status: 'confirmed'
          };

          await postBooking(bookingData);
          store.dispatch('showSnackbar', {
            message: '预约成功',
            color: 'success'
          });
          emit('booking-success');
          closeDialog();
        } catch (error) {
          errorMessage.value = error.message;
          store.dispatch('showSnackbar', {
            message: '预约失败: ' + error.message,
            color: 'error'
          });
        } finally {
          isLoading.value = false;
        }
      }
    };

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    const submitBooking = async () => {
      if (form.value.validate()) {
        isLoading.value = true;
        errorMessage.value = '';
        try {
          // 验证会员ID是否存在
          const member = await getMemberById(memberId.value);
          if (!member) {
            throw new Error('会员ID不存在');
          }

          const bookingData = {
            member_id: memberId.value,
            course_id: selectedCourse.value,
            booking_time: bookingTime.value,
            status: 'confirmed'
          };

          await postBooking(bookingData);
          store.dispatch('showSnackbar', {
            message: '预约成功',
            color: 'success'
          });
          emit('booking-success');
          closeDialog();
        } catch (error) {
          errorMessage.value = error.message;
          store.dispatch('showSnackbar', {
            message: '预约失败: ' + error.message,
            color: 'error'
          });
        } finally {
          isLoading.value = false;
        }
      }
    };